from .base import LanguageController, register_controller


@register_controller("VLA")
class VLAController(LanguageController):
    """Vision-language-action controller: turns a language-typed command into robot motion."""

    def act(self, command, robot):
        raise NotImplementedError
