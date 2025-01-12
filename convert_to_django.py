import os
from lxml import etree

NS = 'http://www.w3.org/2001/XMLSchema'
NS_PREFIX = '{' + NS + '}'

def name_to_camel_case(name):
    return name.replace('_', ' ').title().replace(' ', '')

def check_field_name(name):
    if 'type' == name:
        return 'type_1'
    return name

django_models_path = os.path.join('django-westwood', 'westwood', 'models.py')

if os.path.exists(django_models_path):
    print(django_models_path + ' already exists! Overwriting...\n')

with open(django_models_path, 'w') as models_file:
    models_file.write('from django.db import models\n\n')

    models = {}

    enum_list = [os.path.join('xsd', 'enumerations', 'type.xsd'),
                 os.path.join('xsd', 'enumerations', 'learn_method.xsd'),
                 ]

    # Schemas must be processed in a particular order
    schema_list = [os.path.join('xsd', 'game.xsd'),
                   os.path.join('xsd', 'types.xsd'),
                   os.path.join('xsd', 'pokemon.xsd'),
                   os.path.join('xsd', 'move.xsd'),
                   os.path.join('xsd', 'ability.xsd'),
                   os.path.join('xsd', 'learn_methods.xsd'),
                   os.path.join('xsd', 'learnset.xsd'),
                   os.path.join('xsd', 'tm_set.xsd'),
                   os.path.join('xsd', 'item.xsd'),
                   os.path.join('xsd', 'type_effectiveness.xsd'),
                   os.path.join('xsd', 'nature.xsd'),
                   os.path.join('xsd', 'form.xsd'),
                   os.path.join('xsd', 'rom_hack.xsd'),
                   os.path.join('xsd', 'tutor_set.xsd'),
                   ]

    for enum_file in enum_list:
        try:
            root = etree.parse(enum_file)
            print('\nProcessing ' + enum_file + '\n')

            for element in root.iter(NS_PREFIX + 'simpleType'):
                class_name = element.get('name')
                if class_name:
                    class_name = class_name[0].upper() + class_name[1:]
                    class_name = class_name.replace('Pokemon', '')
                    models[class_name] = '    value = models.CharField(max_length=50)    # Enumeration\n'

        except etree.XMLSyntaxError:
            print('INVALID: ' + enum_file)

    for schema_file in schema_list:
        try:
            root = etree.parse(schema_file)
            print('\nProcessing ' + schema_file + '\n')

            for element in root.iter(NS_PREFIX + 'element'):
                # If this xs:element has children, treat it as a complexType
                if len(list(element)) > 0:
                    class_name = element.get('name')
                    if class_name:
                        # Convert the name to CamelCase
                        class_name = name_to_camel_case(class_name)

                        # If there is a single child xs:element with minOccurs=1, treat it as a list
                        child_elements = element.xpath(".//xs:element[@minOccurs='1']", namespaces={'xs': NS})
                        original_class_name = class_name

                        # Checking for plural with an 's' character is icky, but not sure how else to ensure model reference validity
                        if 's' == original_class_name[-1]:
                            original_class_name = original_class_name[:-1]

                        is_list_element = False
                        if len(child_elements) == 1:
                            class_name += 'ListElement'
                            is_list_element = True

                        # Track this model if we haven't seen it yet
                        if None == models.get(class_name):
                            content = ''

                            if is_list_element:
                                content += '    list_id = models.IntegerField()\n'
                                content += '    sequence_number = models.IntegerField()\n'
                                content += '    element = models.ForeignKey(' + original_class_name + ', on_delete=models.CASCADE)\n'

                            # Find all the simple xs:elements to describe the model's fields
                            child_elements = element.xpath(".//xs:element[not(@minOccurs='1')]", namespaces={'xs': NS})
                            for field in child_elements:
                                name = field.get('name')
                                if name:
                                    name = check_field_name(name)
                                    content += '    ' + name + ' = models.' 
                                    if field.get('type') == 'xs:string':
                                        minOccurs = field.get('minOccurs')
                                        if minOccurs == '0':
                                            content += 'CharField(max_length=500, null=True)'
                                        else:
                                            content += 'CharField(max_length=500)'
                                    elif field.get('type') == 'xs:positiveInteger' or field.get('type') == 'xs:integer':
                                        content += 'IntegerField(default=0)'
                                    elif field.get('type') == 'xs:date':
                                        content += 'DateTimeField()'
                                    else:
                                        # Assume string type by default. This includes types like Westwood enumerations.
                                        content += 'CharField(max_length=500)'
                                    content += '\n'
                                else:
                                    ref = field.get('ref')
                                    if ref:
                                        ref_model = models.get(name_to_camel_case(ref))
                                        if not ref_model:
                                            # Could be a ListElement, try again with suffix
                                            ref_model = models.get(name_to_camel_case(ref) + 'ListElement')

                                        if ref_model:
                                            if 'list_id' in ref_model:
                                                content += '    ' + ref + ' = models.IntegerField()    # ' + name_to_camel_case(ref) + ' list_id\n'
                                            else:
                                                content += '    ' + ref + ' = models.ForeignKey(' + name_to_camel_case(ref) + ', on_delete=models.CASCADE)\n'
                                        else:
                                            print('WARNING: Reference "' + ref + '" used before being defined')

                            models[class_name] = content
                            print('New class: ' + class_name)
                        else:
                            print('Duplicate class: ' + class_name)

        except etree.XMLSyntaxError:
            print('INVALID: ' + schema_file)

    print('\nModels:\n')

    for name in models.keys():
        print(name)
        models_file.write('class ' + name + '(models.Model):\n')
        models_file.write(models[name] + '\n')
