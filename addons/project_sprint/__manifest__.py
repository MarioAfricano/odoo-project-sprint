{
    'name': "Project Sprints",
    'version': '18.0.1.0.0',
    'summary': "Sprint Addon to Odoo",
    'author': "Mário Ferreira",
    'category': 'Services/Project',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_team_views.xml',
        'views/project_sprint_views.xml',
        'views/project_task_views.xml',
        'wizard/project_sprint_close_wizard_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/project_sprint_demo.xml',
    ],
    'installable': True,
    'application': False
}