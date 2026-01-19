import colorama
from django.contrib.admin.sites import site
import inspect

import api.models
from api.models.abstract.soft_delete_model import SoftDeleteModel
from api.admin.abstract.soft_delete_model_admin import SoftDeleteModelAdmin
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    def test_classes(self):
        """
        Ensures all models that inherit from SoftDeleteModel and are registered
        in the admin inherited from SoftDeleteModelAdmin when registering.
        """
        color = colorama.Fore.LIGHTYELLOW_EX
        bright = colorama.Style.BRIGHT
        reset = colorama.Style.RESET_ALL
        for model_name, model_class in inspect.getmembers(api.models):
            if inspect.isclass(model_class) and site.is_registered(model_class):
                if not issubclass(model_class, SoftDeleteModel):
                    continue
                admin_class = site._registry[model_class]
                is_subclass = issubclass(type(admin_class), SoftDeleteModelAdmin)
                if not is_subclass:
                    errors = [
                        f'"{model_name}" model inherits from SoftDeleteModel ',
                        'and is registered in the admin,',
                        "\n",
                        'but the admin class does not inherit from ',
                        'SoftDeleteModelAdmin',
                    ]
                    print(bright + color + ''.join(errors) + reset)
                self.assertTrue(is_subclass)
