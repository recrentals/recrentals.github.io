
def make_flask_proxy():
    import os
    import logging
    import re

    import flask

    OriginalFlask = flask.Flask
    cwd = os.getcwd()

    static_file_re = re.compile(r'\.(css|js)$', re.I)
    def static_file(path):
        if static_file_re.search(path):
            return flask.send_file(os.path.join(os.getcwd(), path))
        else:
            flask.abort(404)

    def favicon():
        return flask.redirect('http://www.codecademy.com/favicon.ico')

    class FlaskProxy(OriginalFlask):

        def __init__(self, *args, **kwargs):
            kwargs['template_folder'] = os.getcwd()
            kwargs['static_folder'] = None
            OriginalFlask.__init__(self, *args, **kwargs)

            self.route('/static/<path:path>')(static_file)
            self.route('/favicon.ico')(favicon)

            self.debug = True

        def run(self, *args, **kwargs):
            kwargs['use_reloader'] = False
            return OriginalFlask.run(self, *args, **kwargs)

    flask.Flask = FlaskProxy


    # Set up logging filter
    access_log_re = re.compile(r'.+?"((?:GET|POST|HEAD|DELETE|PUT) .+)')
    class CodecademyFlaskLogFilter():

        def filter(self, record):
            if record.msg.startswith(' * Running'):
                record.msg = "...Server Running"
                record.args = []
            else:
                match = access_log_re.match(record.msg)
                if match:
                    record.msg = match.group(1).replace('"', '')

            return True

    logger = logging.getLogger('werkzeug')
    logger.addFilter(CodecademyFlaskLogFilter())

make_flask_proxy()
