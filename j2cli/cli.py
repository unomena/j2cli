from __future__ import unicode_literals
from io import open # pylint: disable=redefined-builtin
import os, sys
import argparse

import jinja2
import jinja2.loaders
from . import __version__

from .context import read_context_data, FORMATS
from .extras import filters


class FilePathLoader(jinja2.BaseLoader):
    """ Custom Jinja2 template loader which just loads a single template file """

    def __init__(self, cwd, encoding='utf-8'):
        self.cwd = cwd
        self.encoding = encoding

    def get_source(self, environment, template):
        # Path
        filename = os.path.join(self.cwd, template)

        # Read
        try:
            with open(template, 'rt', encoding=self.encoding) as f:
                contents = f.read()
        except IOError:
            raise jinja2.TemplateNotFound(template)

        # Finish
        uptodate = lambda: False
        return contents, filename, uptodate


def render_template(cwd, template_path, context):
    """ Render a template
    :param template_path: Path to the template file
    :type template_path: basestring
    :param context: Template data
    :type context: dict
    :return: Rendered template
    :rtype: basestring
    """
    env = jinja2.Environment(
        loader=FilePathLoader(cwd),
        undefined=jinja2.StrictUndefined # raises errors for undefined variables
    )

    # Register extras
    env.filters['docker_link'] = filters.docker_link

    return env \
        .get_template(template_path) \
        .render(context)


def render_command(cwd, environ, stdin, argv):
    """ Pure render command
    :param cwd: Current working directory (to search for the files)
    :type cwd: basestring
    :param environ: Environment variables
    :type environ: dict
    :param stdin: Stdin stream
    :type stdin: file
    :param argv: Command-line arguments
    :type argv: list
    :return: Rendered template
    :rtype: basestring
    """
    parser = argparse.ArgumentParser(
        prog='j2',
        description='Command-line interface to Jinja2 for templating in shell scripts.',
        epilog=''
    )
    parser.add_argument('-v', '--version', action='version',
                        version='j2cli {}, Jinja2 {}'.format(__version__, jinja2.__version__))

    parser.add_argument('-f', '--format', default='?', help='Input data format', choices=['?'] + list(FORMATS.keys()))
    parser.add_argument('template', help='Template file to process')
    parser.add_argument('data', nargs='?', default='-', help='Input data path')
    args = parser.parse_args(argv)

    # Input: guess format
    if args.format == '?':
        if args.data == '-':
            args.format = 'env'
        else:
            args.format = {
                '.ini': 'ini',
                '.json': 'json',
                '.yml': 'yaml',
                '.yaml': 'yaml',
                '.env': 'env'
            }[os.path.splitext(args.data)[1]]

    # Input: data
    if args.data == '-' and args.format == 'env':
        input_data_f = None
    else:
        # Warning: assumes utf-8 for input file encoding
        input_data_f = stdin if args.data == '-' else open(args.data, encoding="utf-8")

    # Read data
    context = read_context_data(
        args.format,
        input_data_f,
        environ
    )

    # Render
    return render_template(
        cwd,
        args.template,
        context
    )


def main():
    """ CLI Entry point """
    output = render_command(
        os.getcwd(),
        os.environ,
        sys.stdin,
        sys.argv[1:]
    )
    sys.stdout.write(output)
