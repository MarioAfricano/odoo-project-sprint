from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectSprintCloseWizard(models.TransientModel):
    _name = 'project.sprint.close.wizard'
    _description = 'Close Sprint Wizard'

    sprint_id = fields.Many2one(
        'project.sprint',
        string='Sprint',
        required=True,
    )
    team_id = fields.Many2one(related='sprint_id.team_id')

    open_task_ids = fields.Many2many(
        'project.task',
        string='Unfinished Tasks',
        compute='_compute_open_task_ids',
    )
    open_task_count = fields.Integer(compute='_compute_open_task_ids')

    destination = fields.Selection(
        [
            ('next_sprint', 'Move to another sprint'),
            ('backlog', 'Move to backlog'),
        ],
        string='Destination',
        default='backlog',
        required=True,
    )

    next_sprint_id = fields.Many2one(
        'project.sprint',
        string='Target Sprint',
        domain="[('team_id', '=', team_id), ('state', '=', 'draft')]",
    )

    @api.depends('sprint_id')
    def _compute_open_task_ids(self):
        for wizard in self:
            open_tasks = wizard.sprint_id.task_ids.filtered(lambda t: not t.is_closed)
            wizard.open_task_ids = open_tasks
            wizard.open_task_count = len(open_tasks)

    def action_confirm(self):
        self.ensure_one()

        if self.destination == 'next_sprint' and not self.next_sprint_id:
            raise UserError(_("Please choose the sprint that will receive the unfinished tasks."))

        if self.destination == 'next_sprint':
            target_sprint = self.next_sprint_id.id
        else:
            target_sprint = False

        self.sprint_id.write({'delivered_points': self.sprint_id.points_done})
        self.open_task_ids.write({'sprint_id': target_sprint})
        self.sprint_id.write({'state': 'done'})