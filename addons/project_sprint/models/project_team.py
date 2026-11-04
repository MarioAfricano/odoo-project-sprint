from odoo import fields, models


class ProjectTeam(models.Model):
    _name = 'project.team'
    _description = 'Project Team'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)
    member_ids = fields.Many2many(
        'res.users',
        string='Members',
    )
    sprint_ids = fields.One2many(
        'project.sprint',
        'team_id',
        string='Sprints',
    )