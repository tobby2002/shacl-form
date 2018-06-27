from rdfhandling import RDFHandler
import sys
from rendering import render_template
import os


def generate_webform(filename, form_destination='../miniflask/view/templates/form_contents.html',
                     map_destination='../miniflask/map.ttl'):
    if not filename:
        raise Exception('Usage - python main.py <SHACL file path> <optional: form destination> '
                        '<optional: map destination')
    if not os.path.isfile(filename):
        raise Exception('File does not exist')

    RDF_handler = RDFHandler(filename)

    # Get shape
    shape = RDF_handler.get_shape()

    # Check that the file contained a shape
    if not shape:
        raise Exception('No shape provided in: ' + filename)

    # Get a name for the form by cutting off part of the target class URI to find a more human readable name
    # Example: http://schema.org/Person -> Person
    form_name = shape['target_class'].rsplit('/', 1)[1] if 'target_class' in shape else 'Entry'
    """
    Sort the groups
    This lambda expression uses a tuple to sort items with an order before unordered items. Tuples are compared by their
    first element first, then the second, etc. False sorts before True, so all None values will be sorted to the end
    """
    shape['groups'].sort(key=lambda x: (x['order'] is None, x['order']))
    # Sort properties in groups
    for g in shape['groups']:
        g['properties'].sort(key=lambda x: (x['order'] is None, x['order']))
    # Sort ungrouped properties
    shape['properties'].sort(key=lambda x: (x['order'] is None, x['order']))
    # Sort within composite properties
    for g in shape['groups']:
        for property in g['properties']:
            sort_composite_property(property)
    for property in shape['properties']:
        sort_composite_property(property)

    # Assign every property a unique ID
    next_id = 0
    for g in shape['groups']:
        for property in g['properties']:
            assign_id(property, next_id)
            next_id += 1
    for property in shape['properties']:
        assign_id(property, next_id)
        next_id += 1

    # Link pair property constraints by ID
    for g in shape["groups"]:
        for property in g["properties"]:
            for constraint in property:
                find_paired_properties(shape, property, constraint)
    for property in shape["properties"]:
        for constraint in property:
            find_paired_properties(shape, property, constraint)

    # Put things into template
    os.makedirs(os.path.dirname(os.path.abspath(form_destination)), exist_ok=True)
    with open(form_destination, 'w') as f:
        f.write(render_template(form_name, shape))

    # Create map for converting submitted data into RDF
    RDF_handler.create_rdf_map(shape, map_destination)


def sort_composite_property(property):
    if 'property' in property:
        property['property'].sort(key=lambda x: (x['order'] is None, x['order']))
        for p in property['property']:
            sort_composite_property(p)


def assign_id(property, next_id, parent_id=None):
    # Assigns the property an ID
    # Additionally, assigns an ID to any property within this property
    if parent_id is not None:
        property["id"] = str(parent_id) + ":" + str(next_id)
    else:
        property["id"] = next_id
    if "property" in property:
        next_internal_id = 0
        for p in property["property"]:
            assign_id(p, next_internal_id, parent_id=property["id"])
            next_internal_id += 1


def find_paired_properties(shape, property, constraint):
    # If the constraint is a pair property constraint, iterates through all the properties looking for the one that
    # matches
    # Additionally, looks for pair property constraints in the properties contained in this property using recursion
    if constraint == "property":
        for p in property[constraint]:
            for c in p:
                find_paired_properties(shape, p, c)
    if constraint in ["equals", "disjoint", "lessThan", "lessThanOrEquals"]:
        for g in shape["groups"]:
            for p in g["properties"]:
                result = check_property(p, str(property[constraint]))
                if result is not None:
                    property[constraint] = result
                    return
        for p in shape["properties"]:
            result = check_property(p, str(property[constraint]))
            if result is not None:
                property[constraint] = result
                return


def check_property(property, path):
    # If the property path matches the path being searched for, return the property id
    # Also searches the properties inside this property using recursion
    if str(property["path"]) == path:
        return property["id"]
    if "property" in property:
        for p in property["property"]:
            result = check_property(p, path)
            if result is not None:
                return result


if __name__ == "__main__":
    # File name passed as command-line argument
    if len(sys.argv) >= 4:
        generate_webform(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2:
        generate_webform(sys.argv[1])
    else:
        generate_webform(None)
