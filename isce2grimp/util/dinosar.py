"""
ported from unmaintained dinosar code :) 
"""
import yaml
import os

def write_download_urls(fileList):
    """Write list of frame urls to a file.

    This is useful if you are running isce on a server and want to keep a
    record of download links. Writes download-links.txt to current folder.

    Parameters
    ----------
    fileList : list
        list of download url strings

    """
    with open("download-links.txt", "w") as f:
        f.write("\n".join(fileList))

def read_yaml_template(template=None):
    """Read yaml file."""
    if template is None:
        template = os.path.join(os.path.dirname(__file__), "topsApp-template.yml")
    with open(template, "r") as outfile:
        defaults = yaml.load(outfile, Loader=yaml.FullLoader)

    return defaults


def dict2xml(dictionary, root="topsApp", topcomp="topsinsar"):
    """Convert simple dictionary to XML for ISCE."""

    def add_property(property, value):
        xml = f"        <property name='{property}'>{value}</property>\n"
        return xml

    def add_component(name, properties):
        xml = f"    <component name='{name}'>\n"
        for prop, val in properties.items():
            xml += add_property(prop, val)
        xml += "    </component>\n"
        return xml

    dictionary = dictionary[topcomp]
    xml = f'<{root}>\n   <component name="{topcomp}">\n'
    for key, val in dictionary.items():
        if isinstance(val, dict):
            xml += add_component(key, val)
        else:
            xml += add_property(key, val)

    xml += f"    </component>\n</{root}>\n"

    return xml


def write_xml(xml, outname="topsApp.xml"):
    """Write xml string to a file."""
    print(f"writing {outname}")
    with open(outname, "w") as f:
        f.write(xml)


def load_defaultDict(template):
    if template:
        print(f"Reading from template file: {template}...")
        inputDict = read_yaml_template(template)
    else:
        inputDict = {
            "topsinsar": {
                "sensorname": "SENTINEL1",
                "reference": {"safe": ""},
                "secondary": {"safe": ""},
            }
        }
    return inputDict