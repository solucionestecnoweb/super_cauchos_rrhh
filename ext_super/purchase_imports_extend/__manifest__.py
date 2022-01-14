

{
    "name": "Purchase Imports Extend",
    "version": "13.0.1.0.1",
    "author": "OasisConsultora",
    "maintainer": "OasisConsultora",
    "website": "oasisconsultora.com",
    "license": "AGPL-3",
    "depends": ['base', 'purchase', 'supercauchos_stock', 'sale'],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_imports.xml",
        "views/purchase_order_line_imports.xml",
        "views/purchase_order_imports_payment.xml",
        "views/purchase_order_imports_containers.xml",
        "views/purchase_order_imports_merchandise.xml",
        "views/purchase_order_imports_importations.xml",
        # "views/purchase_order_imports_shipping.xml",
        "views/purchase_order_imports_menu_items.xml",
        "views/sale_order_imports.xml",
        "views/wizard_importations.xml",
        "report/importation_cycle.xml",
        "report/merchandise_in_transit.xml",
        "views/res_company.xml",
    ],
    'installable': True,
}
