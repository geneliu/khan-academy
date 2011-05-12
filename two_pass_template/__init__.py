import logging
import os

from google.appengine.ext.webapp import template
from google.appengine.api import memcache

from app import App
import layer_cache
import request_handler
import monkey_patches

def two_pass_handler():
    def decorator(target):
        # Monkey patch up django template
        monkey_patches.patch()

        def wrapper(handler):
            cached_template = TwoPassTemplate.after_first_pass(handler, target)
            handler.response.out.write(cached_template.render_second_pass(handler))

        return wrapper
    return decorator

class TwoPassVariableContext:
    def __init__(self, target_name, args):
        self.target_name = target_name
        self.args = args

def two_pass_variable():
    def decorator(target):
        def wrapper(handler, *args, **kwargs):
            first_pass_call = kwargs.get("first_pass_call", True)
            variable_context_key = "two_pass_template_context[%s][%s]" % (handler.request.path, target.__name__)

            if first_pass_call:
                variable_context = TwoPassVariableContext(target.__name__, args)
                memcache.set(variable_context_key, variable_context, namespace=App.version)
                return variable_context
            else:
                def inner_wrapper(handler, *args, **kwargs):
                    variable_context = memcache.get(variable_context_key, namespace=App.version)
                    return target(handler, *variable_context.args)
                return inner_wrapper

        return wrapper
    return decorator

class TwoPassTemplate():

    def __init__(self, source, template_value_fxn_names):
        self.source = source
        self.template_value_fxn_names = template_value_fxn_names

    def render_second_pass(self, handler):
        compiled_template = template.Template(self.source)
        second_pass_template_values = {}

        for key in self.template_value_fxn_names:
            wrapped_fxn = getattr(handler, self.template_value_fxn_names[key])
            second_pass_template_values[key] = wrapped_fxn(first_pass_call=False)(handler)

        return compiled_template.render(second_pass_template_values)

    @staticmethod
    def after_first_pass(handler, target):
        template_source, template_value_fxn_names = TwoPassTemplate.render_first_pass(handler, target)
        return TwoPassTemplate(template_source, template_value_fxn_names)

    @staticmethod
#    @layer_cache.cache_with_key_fxn(
#            lambda handler, target: "two_pass_template[%s]" % handler.request.path, 
#            layer=layer_cache.Layers.Memcache
#            )
    def render_first_pass(handler, target):

        template_name, template_values = target(handler)
        template_value_fxn_names = {}

        # Remove two pass variable contexts for first pass render,
        # and keep references around for second pass
        for key in template_values.keys():
            val = template_values[key]
            if isinstance(val, TwoPassVariableContext):
                template_value_fxn_names[key] = val.target_name
                del template_values[key]

        path = os.path.join(os.path.dirname(__file__), "..", template_name)

        try:
            monkey_patches.enable_first_pass_variable_resolution(True)
            first_pass_source = template.render(path, template_values)
        finally:
            monkey_patches.enable_first_pass_variable_resolution(False)

        return (first_pass_source, template_value_fxn_names)

class TwoPassTest(request_handler.RequestHandler):

    @two_pass_variable()
    def sheep(self, monkey):
        return monkey + self.request_int("inc", default=1)

    @two_pass_variable()
    def donkey(self, gorilla):
        return gorilla + self.request_int("inc", default=1)

    @two_pass_variable()
    def zebras(self):
        return "hrm"

    @two_pass_handler()
    def get(self):

        monkey = 5
        gorilla = 6

        template_values = {
            "sheep": self.sheep(monkey),
            "donkey": self.donkey(gorilla),
            "zebras": self.zebras(),
            "monkey": "ooh ooh aah aah",
        }

        return ("two_pass_template/two_pass_test.html", template_values)

