# Copyright 2020 GregorioCode <Info@gregoriocode.com>


{
    "name": "Sale Logic Extend",
    "version": "13.0.1.0.1",
    "author": "Oasis Consultora",
    "website": "https://gregoriocode.com",
    "license": "AGPL-3",
    "depends": ['base', 'sale', 'contacts','isrl_retention', 'l10n_ve_fiscal_requirements'],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_logic_extend.xml",
        "views/res_partner_logic_extend.xml",
    ],
    'installable': True,
}
