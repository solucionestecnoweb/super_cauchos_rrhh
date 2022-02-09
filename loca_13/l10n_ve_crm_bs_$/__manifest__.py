{
    'name': "Localizacion Venezolana Moneda en divisa y campo metas con fecha en CRM",

    'summary': """Moneda en divisa y campo metas con fecha en CRM""",

    'description': """
       Moneda en divisa y campo metas con fecha en CRM

    """,
    'version': '2.0',
    'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A',
    'category': 'Tools',
    'website': 'http://soluciones-tecno.com/',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','crm_enterprise','l10n_ve_asientos_bs_$_account'],

    # always loaded
    'data': [
    'vista/crm_lead_inherit_view.xml',
    'security/ir.model.access.csv',
    'date/date_plazo_meta.xml',
    ],
    'application': True,
}
