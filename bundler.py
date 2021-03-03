"""Build Process
"""
import sys
import os
import subprocess
import re
import copy
import json


class Bundler(object):
    """Bundles all the model files into a single API document
    
    Notes
    -----
    - Bundles multiple OpenAPI v3.x yaml files into a single file.
    - Does not inline schemas indicated by ref keywords but normalizes them by 
      removing the file path. 
    - Validates the bundled file
    
    Args
    ----
        api_filename (str): The filename of the toplevel API
        output_filename (str): The filename of the resolved API
    """
    def __init__(self,
                 api_filename,
                 output_filename,
                 validate=True):
        self.__python = os.path.normpath(sys.executable)
        self.__python_dir = os.path.dirname(self.__python)
        self._content = {}
        self._includes = {}
        self._resolved = []
        self._validate = validate
        self._output_filename = output_filename
        api_filename = os.path.normpath(os.path.abspath(api_filename))
        self._base_dir = os.path.dirname(api_filename)
        self._api_filename = os.path.basename(api_filename)
        self._install_dependencies()

    def _install_dependencies(self):
        packages = ['pyyaml', 'jsonpath-ng', 'openapi-spec-validator']
        for package in packages:
            print('installing dependency %s...' % package)
            process_args = [
                self.__python, '-m', 'pip', 'install', '-U', package
            ]
            process = subprocess.Popen(process_args, shell=False)
            process.wait()

    def bundle(self):
        self._bundle(self._base_dir, self._api_filename, self._output_filename)
        return self

    def validate(self):
        self._validate_file()
        return self

    def _bundle(self, base_dir, api_filename, output_filename):
        """Start at the file that contains the paths and bundle all 
        dependent files into one openapi.yaml file.
        """
        print('bundling started')
        self._read_file(base_dir, api_filename)
        self._resolve_x_include()
        self._resolve_x_pattern('x-field-pattern')
        self._resolve_x_pattern('x-device-pattern')
        self._resolve_strings(self._content)
        with open(self._output_filename, 'w') as fid:
            yaml.dump(self._content,
                      fid,
                      indent=2,
                      allow_unicode=True,
                      line_break='\n',
                      sort_keys=False)
        with open('openapi.json', 'w') as fp:
            fp.write(json.dumps(self._content, indent=4))         
        print('bundling complete')

    def _validate_file(self):
        if self._validate is False:
            return
        print('validating started')
        with open(self._output_filename) as fid:
            yobject = yaml.safe_load(fid)
            openapi_spec_validator.validate_v3_spec(yobject)
        print('validating complete')

    def _read_file(self, base_dir, filename):
        filename = os.path.join(base_dir, filename)
        filename = os.path.abspath(os.path.normpath(filename))
        base_dir = os.path.dirname(filename)
        with open(filename) as fid:
            yobject = yaml.safe_load(fid)
        self._process_yaml_object(base_dir, yobject)

    def _process_yaml_object(self, base_dir, yobject):
        for key, value in yobject.items():
            if key in ['openapi', 'info', 'servers'] and key not in self._content.keys():
                self._content[key] = value
            elif key in ['paths']:
                if key not in self._content.keys():
                    self._content[key] = {}
                for sub_key in value.keys():
                    self._content[key][sub_key] = value[sub_key]
            elif key == 'components':
                if key not in self._content.keys():
                    self._content[key] = {'responses': {}, 'schemas': {}}
                self._validate_names('^[+a-zA-Z0-9_]+$', 'schemas', value)
                self._validate_names('^[+a-zA-Z0-9_]+$', 'responses', value)
        self._resolve_refs(base_dir, yobject)

    def _validate_names(self, regex, components_key, components):
        if components_key not in components:
            return
        objects = components[components_key]
        for key, value in objects.items():
            if 'properties' in objects[key]:
                for name in objects[key]['properties']:
                    if re.match(regex, name) is None:
                        raise NameError(
                            '%s property name `%s` contains invalid characters'
                            % (key, name))
            self._content['components'][components_key][key] = value

    def _resolve_refs(self, base_dir, yobject):
        """Resolving references is relative to the current file location
        """
        if isinstance(yobject, dict):
            for key, value in yobject.items():
                if key == '$ref' and value.startswith('#') is False:
                    refs = value.split('#')
                    if refs[1] not in self._resolved:
                        self._resolved.append(refs[1])
                        print('resolving %s' % value)
                        self._read_file(base_dir, refs[0])
                    yobject[key] = '#%s' % refs[1]
                elif isinstance(value, str) and 'x-inline' in value:
                    refs = value.split('#')
                    print('inlining %s' % value)
                    inline = self._get_inline_ref(base_dir, refs[0], refs[1])
                    yobject[key] = inline
                elif key == 'x-include':
                    for include_ref in value:
                        if include_ref not in self._includes:
                            include = self._get_schema_object(base_dir, include_ref)
                            self._resolve_refs(base_dir, include)
                            self._includes[include_ref] = include
                else:
                    self._resolve_refs(base_dir, value)
        elif isinstance(yobject, list):
            for item in yobject:
                self._resolve_refs(base_dir, item)

    def _resolve_x_pattern(self, pattern_extension):
        """Find all instances of pattern_extension in the openapi content
        and generate a #/components/schemas/... pattern schema object that is
        specific to the property hosting the pattern extension content.
        Replace the x-field-pattern schema with a $ref to the generated schema.
        """
        import jsonpath_ng
        for xpattern_path in jsonpath_ng.parse('$..{}'.format(pattern_extension)).find(self._content):
            print('generating %s...' % (str(xpattern_path.full_path)))
            object_name = xpattern_path.full_path.left.left.left.right.fields[0]
            property_name = xpattern_path.full_path.left.right.fields[0]
            property_schema = jsonpath_ng.Parent().find(xpattern_path)[0].value
            xpattern = xpattern_path.value
            schema_name = 'Pattern.{}.{}'.format(
                ''.join([piece[0].upper() + piece[1:] for piece in object_name.split('_')]),
                ''.join([piece[0].upper() + piece[1:] for piece in property_name.split('_')])
            )
            format = None
            type_name = xpattern['format']
            if type_name in ['ipv4', 'ipv6', 'mac', 'enum']:
                format = type_name
                type_name = 'string'
            description = 'TBD'
            if 'description' in xpattern:
                description = xpattern['description']
            elif 'description' in property_schema:
                description = property_schema['description']

            if xpattern['format'] == 'checksum':
                self._generate_checksum_schema(xpattern, schema_name, description)
            else:
                self._generate_value_schema(xpattern, schema_name, description, type_name, format)

            property_schema['$ref'] = '#/components/schemas/{}'.format(
                schema_name
            )
            del property_schema[pattern_extension]

    def _generate_checksum_schema(self, xpattern, schema_name, description):
        """ Generate a checksum schema object
        """
        schema = {
            'description': description,
            'type': 'object',
            'required': ['choice'],
            'properties': {
                'choice': {
                    'description': 'The type of checksum',
                    'type': 'string',
                    'enum': ['generated', 'custom'],
                    'default': 'generated'
                },
                'generated': {
                    'description': 'A system generated checksum value',
                    'type': 'string',
                    'enum': ['good', 'bad'],
                    'default': 'good'
                },
                'custom': {
                    'description': 'A custom checksum value',
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 2**int(xpattern['length']) - 1
                }
            }
        }
        self._content['components']['schemas'][schema_name] = schema

    def _generate_value_schema(self, xpattern, schema_name, description, type_name, format):
        xconstants = xpattern['x-constants'] if 'x-constants' in xpattern else None
        schema = {
            'description': description,
            'type': 'object',
            'required': ['choice'],
            'properties': {
                'choice': {
                    'type': 'string',
                    'enum': ['value', 'values'],
                    'default': 'value'
                },
                'value': {
                    'type': copy.deepcopy(type_name)
                },
                'values': {
                    'type': 'array',
                    'items': {
                        'type': copy.deepcopy(type_name)
                    }
                }
            }
        }
        if xconstants is not None:
            schema['x-constants'] = copy.deepcopy(xconstants)
        if 'features' in xpattern:
            if 'auto' in xpattern['features']:
                schema['properties']['choice']['enum'].append('auto')
                schema['properties']['choice']['default'] = 'auto'
                schema['properties']['auto'] = {
                    'type': 'string',
                    'enum': ['auto'],
                    'default': 'auto'
                }
            if 'metric_group' in xpattern['features']:
                schema['properties']['metric_group'] = {
                    'description': """A unique name is used to indicate to the system that the field may """ 
                                   """extend the metric row key and create an aggregate metric row for """ 
                                   """every unique value. """
                                   """To have metric group columns appear in the flow metric rows the flow """ 
                                   """metric request allows for the metric_group value to be specified """
                                   """as part of the request.""",
                    'type': 'string'
                }
        if 'enums' in xpattern:
            schema['properties']['value']['enum'] = copy.deepcopy(xpattern['enums'])
            schema['properties']['values']['items']['enum'] = copy.deepcopy(xpattern['enums'])
        if xpattern['format'] in ['integer', 'ipv4', 'ipv6', 'mac']:
            counter_pattern_name = '{}.Counter'.format(schema_name)
            schema['properties']['choice']['enum'].extend(['increment', 'decrement'])
            schema['properties']['increment'] = {
                '$ref': '#/components/schemas/{}'.format(counter_pattern_name)
            }
            schema['properties']['decrement'] = {
                '$ref': '#/components/schemas/{}'.format(counter_pattern_name)
            }
            counter_schema = {
                'description': '{} counter pattern'.format(xpattern['format']),
                'type': 'object',
                'required': ['start', 'step'],
                'properties': {
                    'start': {
                        'type': type_name
                    },
                    'step': {
                        'type': type_name
                    }
                }
            }
            if 'features' in xpattern and 'count' in xpattern['features']:
                counter_schema['properties']['count'] = {
                    'type': 'integer',
                    'default': 1
                }
            self._apply_common_x_field_pattern_properties(counter_schema['properties']['start'], xpattern, format)
            self._apply_common_x_field_pattern_properties(counter_schema['properties']['step'], xpattern, format)
            if xconstants is not None:
                counter_schema['x-constants'] = copy.deepcopy(xconstants)
            self._content['components']['schemas'][counter_pattern_name] = counter_schema
        self._apply_common_x_field_pattern_properties(schema['properties']['value'], xpattern, format)
        self._apply_common_x_field_pattern_properties(schema['properties']['values']['items'], xpattern, format)
        self._content['components']['schemas'][schema_name] = schema

    def _apply_common_x_field_pattern_properties(self, schema, xpattern, format):
        if 'default' in xpattern:
            schema['default'] = xpattern['default']
        if format is not None:
            schema['format'] = format
        if 'length' in xpattern:
            schema['minimum'] = 0
            schema['maximum'] = 2**int(xpattern['length']) - 1
            
    def _resolve_x_include(self):
        """Find all instances of x-include in the openapi content
        and merge the x-include content into the parent object
        """
        import jsonpath_ng
        for xincludes in jsonpath_ng.parse('$..x-include').find(self._content):
            print('resolving %s...' % (str(xincludes.full_path)))
            parent_schema_object = jsonpath_ng.Parent().find(xincludes)[0].value
            for xinclude in xincludes.value:
                include_schema_object = self._includes[xinclude]
                self._merge(copy.deepcopy(include_schema_object), parent_schema_object)
            del parent_schema_object['x-include']

    def _merge(self, src, dst):
        """
        Recursively update a dict.
        Subdict's won't be overwritten but also updated.
        """
        for key, value in src.items(): 
            if key not in dst:
                dst[key] = value
            elif isinstance(value, list):
                for item in value:
                    if item not in dst[key]:
                        dst[key].append(item)
            elif isinstance(value, dict):
                self._merge(value, dst[key]) 
            elif key == 'description':
                dst[key] = '{}\n{}'.format(dst[key], value) 
        return dst

    def _get_schema_object(self, base_dir, schema_path):
        import jsonpath_ng
        json_path = "$..'%s'" % schema_path.split('/')[-1]
        schema_object = jsonpath_ng.parse(json_path).find(self._content)
        if len(schema_object) == 0:
            schema_object = self._get_schema_object_from_file(base_dir, schema_path)
        else:
            schema_object = schema_object[0].value
        return schema_object

    def _get_schema_object_from_file(self, base_dir, schema_path):
        import jsonpath_ng
        paths = schema_path.split('#')
        filename = os.path.join(base_dir, paths[0])
        filename = os.path.abspath(os.path.normpath(filename))
        with open(filename) as fid:
            schema_file = yaml.safe_load(fid)
        json_path = "$..'%s'" % schema_path.split('/')[-1]
        schema_object = jsonpath_ng.parse(json_path).find(schema_file)[0].value
        return schema_object

    def _get_inline_ref(self, base_dir, filename, inline_key):
        import jsonpath_ng
        filename = os.path.join(base_dir, filename)
        filename = os.path.abspath(os.path.normpath(filename))
        base_dir = os.path.dirname(filename)
        with open(filename) as fid:
            yobject = yaml.safe_load(fid)
        return jsonpath_ng.parse('$%s' % inline_key.replace('/', '.'), ).find(yobject)[0].value

    def _resolve_strings(self, content):
        """Fix up strings
        """
        for key, value in content.items():
            if isinstance(value, dict):
                self._resolve_strings(value)
            elif key == 'description':
                descr = copy.deepcopy(value)
                content[key] = description(descr)


if __name__ == '__main__':
    bundler = Bundler(api_filename='./api/api.yaml',
                      output_filename='./openapi.yaml',
                      validate=True)

    import yaml
    import openapi_spec_validator

    class description(str):
        pass

    def description_representer(dumper, data):
        return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                       data,
                                       style='|')

    yaml.add_representer(description, description_representer)

    bundler.bundle().validate()
