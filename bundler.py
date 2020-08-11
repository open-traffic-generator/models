"""Build Process
"""
import yaml
import json
import os
import subprocess
import shutil
import openapi_spec_validator
import datetime


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
    def __init__(self, api_filename, output_filename, dependencies=True):
        self._dependencies = dependencies
        self._output_filename = output_filename
        self._build_dir = os.path.dirname(os.path.abspath(__file__))
        self._python_sdk_dir = os.path.join(self._build_dir, 'python_sdk')
        shutil.rmtree(self._python_sdk_dir, ignore_errors=True)
        os.mkdir(self._python_sdk_dir)
        api_filename = os.path.normpath(os.path.abspath(api_filename))
        self._base_dir = os.path.dirname(api_filename)
        self._api_filename = os.path.basename(api_filename)

    def dependencies(self, packages):
        if self._dependencies is True:
            for package in packages:
                print('installing dependency %s...' % package)
                process_args = [
                    'pip',
                    'install',
                    '-U',
                    package
                ]
                process = subprocess.Popen(process_args, shell=True)
                process.wait()
        return self

    def bundle(self):
        self._bundle(self._base_dir, self._api_filename, self._output_filename)
        return self

    def validate(self):
        self._validate(self._output_filename)
        return self

    def generate_python_sdk(self):
        model_file = os.path.normpath(os.path.join(self._python_sdk_dir, 'datamodels.py'))
        with open(model_file, 'w') as fid:
            fid.write('"""Abstract Traffic Generator API\n')
            fid.write('\tgenerated at %s\n' % datetime.datetime.now())
            fid.write('"""\n')
            fid.write('from typing import Union, List, Dict\n')
            fid.write('import json\n\n\n')
            for name, schema in self._content['components']['schemas'].items():
                self._write_message(fid, name, schema, 1)
        return self
        
    def _write_type(self, fid, property_name, type_schema, index = 1, is_repeatable=False):
        """type_schema can be one of the following:
            - type: integer
            - type: string
            - $ref: '#/components/schemas/Counter'
            - $ref: '#/components/schemas/Random'
        """
        if 'array' in type_schema.values():
            item = type_schema['items']
            return self._write_type(fid, property_name, item, index, True)
        elif '$ref' in type_schema:
            value = type_schema['$ref']
            ref = value.split('/')[-1]
            return ref
        elif 'oneOf' in type_schema:
            """
            key='dst'
            schema='oneOf: ...'
                dst: Union[str, number, List[str], List[int], Count, Random] = '00:00:00:00:00:00'
            """
            union = []
            for item in type_schema['oneOf']:
                union.append(self._write_type(fid, property_name, item))
            return 'Union[%s] = None' % ', '.join(union)
        elif 'anyOf' in type_schema:
            # TBD: fix this by doing a replacement and then process
            return ''
            # fid.write('anyof %s {\n' % property_name)
        else:
            type = type_schema['type']
            if type in ['number', 'integer'] is True:
                type = 'int'
            elif type in ['boolean'] is True:
                type = 'bool'
            elif type in ['string'] is True:
                type = 'str'
            if is_repeatable is True:
                type = 'List[%s]' % type
            return type

    def _write_properties(self, fid, schema, index=1):
        properties = []
        if 'properties' not in schema:
            return properties
        for key, value in schema['properties'].items():
            type = self._write_type(fid, key, value, index)
            properties.append((key, '%s: %s' % (key, type)))
        return properties

    def _write_message(self, fid, name, schema, index):
        fid.write('class %s(object):\n' % name) 
        fid.write('%s"""%s class\n\n' % ('\t' * 1, name))
        if 'description' in schema:
            for sentence in schema['description'].split('\r'):
                fid.write('%s%s\n' % ('\t' * 1, sentence))
        fid.write('%s"""\n' % ('\t' * 1))
        properties = self._write_properties(fid, schema)
        hints = ''
        for prop_name, prop_type in properties:
            hints += (', %s: %s = None' % (prop_name, prop_name)) 
        fid.write('%sdef __init__(self%s):\n' % ('\t' * 1, hints)) 
        for prop_name, prop_type in properties:
            fid.write('%sself.%s = %s:\n' % ('\t' * 2, prop_name, prop_name)) 
        if 'allOf' in schema: # process inner messages
            for item in schema['allOf']: 
                if '$ref' in item:
                    property_name = item['$ref'].split('/')[-1].lower()
                    index = self._write_type(fid, property_name, item, index)
                else:
                    index = self._write_properties(fid, item, index)
        fid.write('\n\n\n')

    def generate_sdk(self):
        self._generate_sdk(self._output_filename)
        self._patch_python_sdk()
        return self

    def install_sdk(self):
        self._install_sdk()

    def _bundle(self, base_dir, api_filename, output_filename):
        print('bundling...')
        self._content = {}
        self._read_file(base_dir, api_filename, None)
        components = self._content['components']
        self._content['components'] = {}
        self._content['components']['schemas'] = components
        self._output_filename = os.path.normpath(os.path.join(self._python_sdk_dir, output_filename))
        with open(self._output_filename, 'w') as fid:
            yaml.dump(self._content, fid, indent=2, sort_keys=False)

    def _install_sdk(self):
        process_args = [
            'python',
            'setup.py',
            'install'
        ]
        pkg_dir = os.path.normpath(os.path.join(self._sdk_dir, 'python_generic_lib'))
        process = subprocess.Popen(process_args, 
            cwd=pkg_dir, shell=True)
        process.wait()
        if process.returncode != 0:
            raise Exception(process.errors)
               
    def _generate_sdk(self, output_filename):
        for target in ['python_generic_lib', 'go_generic_lib']:
            process_args = [
                "apimatic-cli",
                "generate", 
                "fromuser", 
                "--platform", 
                target, 
                "--name", 
                "athena", 
                "--email", 
                "andy.balogh@keysight.com", 
                "--password", 
                "BingBang0", 
                "--file", 
                "athena.yaml", 
                "--download-as", 
                target + '.zip',
            ]
            process = subprocess.Popen(process_args, shell=True)
            process.wait()
            if process.returncode != 0:
                raise Exception(process.errors)

    def _patch_python_sdk(self):
        init_path = os.path.join(self._sdk_dir, 'python_generic_lib', 'athena', '__init__.py')
        with open(init_path, 'w') as fid:
            import pathlib
            filenames = pathlib.Path().glob("%s/**/*.py" % os.path.join(self._sdk_dir, 'python_generic_lib', 'athena'))
            for filename in filenames:
                if filename.name != '__init__.py' and filename.name.endswith('.py'):
                    line = 'from %s import *\n' % '.'.join(filename.parts[2:])[:-3]
                    fid.write(line)

        api_helper_path = os.path.join(self._sdk_dir, 'python_generic_lib', 'athena', 'api_helper.py')
        with open(api_helper_path) as fid:
            content = fid.readlines()
        with open(api_helper_path, 'w') as fid:
            fid.write(''.join(content[0:329]))
            fid.write('                # patch code to suppress serialization of null values\n')
            fid.write('                value = APIHelper.to_dictionary(value) if hasattr(value, "_names") else value\n')
            fid.write('                if value is not None:\n')
            fid.write('                    dictionary[obj._names[name]] = value\n\n')
            fid.write(''.join(content[331:]))

    def _validate(self, output_filename):
        print('validating...')
        with open(output_filename) as fid:
            yobject = yaml.safe_load(fid)
            openapi_spec_validator.validate_v3_spec(yobject)

    def _finditem(self, obj, key):
        if key in obj: 
            return obj[key]
        for k, v in obj.items():
            if isinstance(v,dict):
                item = self._finditem(v, key)
                if item is not None:
                    return item
        return None

    def _read_file(self, base_dir, filename, parent):
        filename = os.path.join(base_dir, filename)
        filename = os.path.abspath(os.path.normpath(filename))
        base_dir = os.path.dirname(filename)
        with open(filename) as fid:
            yobject = yaml.safe_load(fid)
        if parent == 'allOf':
            for property_key, property_value in yobject['components']:  
                self._content[parent]['properties'][property_key] = property_value
        else:
            self._process_yaml_object(base_dir, yobject, parent)

    def _process_yaml_object(self, base_dir, yobject, parent):
        for key in yobject.keys():
            if key not in self._content:
                self._content[key] = None
            value = yobject[key]
            if key in ['openapi', 'info', 'servers'] and self._content[key] is None:
                self._content[key] = value
            elif key in ['paths']:
                if self._content[key] is None:
                    self._content[key] = {}
                for sub_key in value.keys():
                    self._content[key][sub_key] = value[sub_key] 
            elif key == 'components':
                if self._content[key] is None:
                    self._content[key] = {}
                if 'schemas' in value:
                    schemas = value['schemas']
                    for schema_key in schemas.keys():
                        self._content[key][schema_key] = schemas[schema_key]
                        self._resolve(base_dir, schemas[schema_key], parent)
                        
    def _resolve(self, base_dir, schema, parent):
        if isinstance(schema, dict):
            for key in schema.keys():
                if key == '$ref' and schema[key].startswith('#') is False:
                    refs = schema[key].split('#')
                    schema[key] = '#' + refs[1]
                    self._read_file(base_dir, refs[0], parent)
                else:
                    self._resolve(base_dir, schema[key], key)
        elif isinstance(schema, list):
            for item in schema:
                self._resolve(base_dir, item, parent)
            

if __name__ == '__main__':
    build = Bundler('./api/api.yaml', './open-traffic-generator.yaml', dependencies=False)
    build.dependencies(['pyyaml', 'openapi-spec-validator']) \
        .bundle() \
        # .validate() \
