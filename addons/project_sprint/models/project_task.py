from odoo import api, fields, models, Command


class ProjectTask(models.Model):
    _inherit = 'project.task'

    sprint_id = fields.Many2one(
        'project.sprint',
        string='Sprint',
        domain="[('state', 'in', ('draft', 'active'))]",
        ondelete='set null',
        index=True,
        tracking=True,
    )
    story_points = fields.Integer(string='Story Points')

    sprint_history_ids = fields.Many2many(
        'project.sprint',
        'project_task_sprint_history_rel',
        'task_id',
        'sprint_id',
        string='Sprint History',
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks.filtered('sprint_id'):
            task.sprint_history_ids = [Command.link(task.sprint_id.id)]
        return tasks

    def write(self, vals):
        if 'sprint_id' in vals:
            for task in self.filtered('sprint_id'):
                task.sprint_history_ids = [Command.link(task.sprint_id.id)]
        res = super().write(vals)
        if vals.get('sprint_id'):
            self.sprint_history_ids = [Command.link(vals['sprint_id'])]
        return res