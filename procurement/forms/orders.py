# filepath: procurement/forms/orders.py
from common.forms import ActionForm


class IssueOrderForm(ActionForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['expected_version'].required = True
