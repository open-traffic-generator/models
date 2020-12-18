"""Build Process
"""
import sys
import os
import subprocess
import re


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
                 dependencies=True,
                 validate=True):
        self.__python = os.path.normpath(sys.executable)
        self.__python_dir = os.path.dirname(self.__python)
        self._content = {}
        self._dependencies = dependencies
        self._validate = validate
        self._output_filename = output_filename
        api_filename = os.path.normpath(os.path.abspath(api_filename))
        self._base_dir = os.path.dirname(api_filename)
        self._api_filename = os.path.basename(api_filename)
        self._install_dependencies()

    def _install_dependencies(self):
        if self._dependencies is False:
            return
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
        print('bundling started')
        self._read_file(base_dir, api_filename)
        self._resolve_strings(self._content)
        with open(self._output_filename, 'w') as fid:
            yaml.dump(self._content,
                      fid,
                      indent=2,
                      allow_unicode=False,
                      sort_keys=False)
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
            if key in ['openapi', 'info', 'servers'
                       ] and key not in self._content.keys():
                self._content[key] = value
            elif key in ['paths']:
                if key not in self._content.keys():
                    self._content[key] = {}
                for sub_key in value.keys():
                    self._content[key][sub_key] = value[sub_key]
            elif key == 'components':
                if key not in self._content.keys():
                    self._content[key] = {'responses': {}, 'schemas': {}}
                if 'schemas' in value:
                    schemas = value['schemas']
                    for schema_key in schemas.keys():
                        if 'properties' in schemas[schema_key]:
                            for name in schemas[schema_key]['properties']:
                                if re.match('^[+a-zA-Z0-9_]+$', name) is None:
                                    raise NameError(
                                        '%s property name `%s` contains invalid characters'
                                        % (schema_key, name))
                        self._content['components']['schemas'][
                            schema_key] = schemas[schema_key]
                if 'responses' in value:
                    schemas = value['responses']
                    for schema_key in schemas.keys():
                        if 'properties' in schemas[schema_key]:
                            for name in schemas[schema_key]['properties']:
                                if re.match('^[+a-zA-Z0-9_]+$', name) is None:
                                    raise NameError(
                                        '%s property name `%s` contains invalid characters'
                                        % (schema_key, name))
                        self._content['components']['responses'][
                            schema_key] = schemas[schema_key]
        self._resolve_refs(base_dir, yobject)

    def _resolve_refs(self, base_dir, yobject):
        """Resolving references is relative to the current file location
        """
        if isinstance(yobject, dict):
            for key, value in yobject.items():
                if key == '$ref' and value.startswith('#') is False:
                    refs = value.split('#')
                    print('resolving %s' % value)
                    self._read_file(base_dir, refs[0])
                    yobject[key] = '#%s' % refs[1]
                elif isinstance(value, str) and 'x-inline' in value:
                    refs = value.split('#')
                    print('inlining %s' % value)
                    inline = self._get_inline_ref(base_dir, refs[0], refs[1])
                    yobject[key] = inline
                else:
                    self._resolve_refs(base_dir, value)
        elif isinstance(yobject, list):
            for item in yobject:
                self._resolve_refs(base_dir, item)

    def _get_inline_ref(self, base_dir, filename, inline_key):
        filename = os.path.join(base_dir, filename)
        filename = os.path.abspath(os.path.normpath(filename))
        base_dir = os.path.dirname(filename)
        with open(filename) as fid:
            yobject = yaml.safe_load(fid)
        import jsonpath_ng
        return jsonpath_ng.parse('$%s' %
                     inline_key.replace('/', '.'), ).find(yobject)[0].value

    def _resolve_strings(self, content):
        """Fix up strings
        """
        for key, value in content.items():
            if isinstance(value, dict):
                self._resolve_strings(value)
            elif key == 'description':
                content[key] = folded_unicode(value)


if __name__ == '__main__':
    bundler = Bundler(api_filename='./api/api.yaml',
                      output_filename='./openapi.yaml',
                      dependencies=False,
                      validate=True)

    import yaml
    import openapi_spec_validator

    class folded_unicode(str):
        pass

    class literal_unicode(str):
        pass

    def folded_unicode_representer(dumper, data):
        return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                       data,
                                       style='>')

    def literal_unicode_representer(dumper, data):
        return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                       data,
                                       style='|')

    yaml.add_representer(folded_unicode, folded_unicode_representer)
    yaml.add_representer(literal_unicode, literal_unicode_representer)

    bundler.bundle().validate()
