# -*- coding: utf-8 -*-
{
    'name': "Campos adicionales en ficha de lista de correos Email Marketing",

    'summary': """Campos adicionales en ficha de lista de correos Email Marketing""",

    'description': """
       Campos adicionales en ficha de lista de correos Email Marketing Super Cauchos
       Colaborador: Ing. Darrell Sojo
    """,
    'version': '1.0',
    'author': 'INM&LDR Soluciones Tecnologicas',
    'category': 'Campos adicionales en ficha de lista de correos Email Marketing Super Cauchos',

    # any module necessary for this one to work correctly
    'depends': ['base','mass_mailing'],

    # always loaded
    'data': [
        'view/mailing_contact_inherit.xml',
        #'view_add.xml',
        #'security/ir.model.access.csv',
    ],
    'application': True,
}
