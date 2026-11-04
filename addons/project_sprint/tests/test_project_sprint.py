from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectSprint(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref('base.user_admin')
        cls.team_alpha = cls.env['project.team'].create({
            'name': 'Test Alpha',
            'member_ids': [(6, 0, cls.user.ids)],
        })
        cls.team_beta = cls.env['project.team'].create({'name': 'Test Beta'})
        cls.project = cls.env['project.project'].create({'name': 'Test Project'})

    def _create_sprint(self, team, start, end, name='Test Sprint'):
        return self.env['project.sprint'].create({
            'name': name,
            'team_id': team.id,
            'date_start': start,
            'date_end': end,
        })

    def _create_task(self, sprint, points, done=False):
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'sprint_id': sprint.id,
            'story_points': points,
        })
        if done:
            task.state = '1_done'
        return task

    def test_end_before_start_raises(self):
        with self.assertRaises(ValidationError):
            self._create_sprint(self.team_alpha, date(2030, 1, 14), date(2030, 1, 1))

    def test_overlap_same_team_raises(self):
        self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        with self.assertRaises(ValidationError):
            self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 15))

    def test_overlap_other_team_allowed(self):
        self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        sprint_beta = self._create_sprint(self.team_beta, date(2030, 1, 1), date(2030, 1, 14))
        self.assertTrue(sprint_beta)

    def test_single_active_sprint_per_team(self):
        sprint_1 = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        sprint_2 = self._create_sprint(self.team_alpha, date(2030, 1, 15), date(2030, 1, 28))
        sprint_1.action_start()
        with self.assertRaises(ValidationError):
            sprint_2.action_start()

    def test_metrics(self):
        sprint = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        self._create_task(sprint, 5, done=True)
        self._create_task(sprint, 3)
        self.assertEqual(sprint.task_count, 2)
        self.assertEqual(sprint.points_total, 8)
        self.assertEqual(sprint.points_done, 5)
        self.assertEqual(sprint.progress, 62.5)

    def test_start_sets_committed_points(self):
        sprint = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        self._create_task(sprint, 5)
        self._create_task(sprint, 3)
        sprint.action_start()
        self.assertEqual(sprint.state, 'active')
        self.assertEqual(sprint.committed_points, 8)

    def test_close_without_open_tasks(self):
        sprint = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        self._create_task(sprint, 5, done=True)
        sprint.action_start()
        result = sprint.action_done()
        self.assertTrue(result)
        self.assertEqual(sprint.state, 'done')
        self.assertEqual(sprint.delivered_points, 5)

    def test_close_wizard_moves_open_tasks(self):
        sprint = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        next_sprint = self._create_sprint(self.team_alpha, date(2030, 1, 15), date(2030, 1, 28))
        done_task = self._create_task(sprint, 5, done=True)
        open_task = self._create_task(sprint, 3)
        sprint.action_start()

        action = sprint.action_done()
        self.assertEqual(action['res_model'], 'project.sprint.close.wizard')
        wizard = self.env['project.sprint.close.wizard'].with_context(action['context']).create({})
        self.assertEqual(wizard.next_sprint_id, next_sprint)
        wizard.action_confirm()

        self.assertEqual(sprint.state, 'done')
        self.assertEqual(sprint.delivered_points, 5)
        self.assertEqual(done_task.sprint_id, sprint)
        self.assertEqual(open_task.sprint_id, next_sprint)
        self.assertIn(sprint, open_task.sprint_history_ids)
        self.assertIn(open_task, sprint.carried_over_task_ids)

    def test_borrowed_members(self):
        outsider = self.env['res.users'].create({'name': 'Outsider', 'login': 'outsider_test'})
        sprint = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        task_member = self._create_task(sprint, 3)
        task_member.user_ids = self.user
        task_outsider = self._create_task(sprint, 2)
        task_outsider.user_ids = outsider
        self.assertEqual(sprint.borrowed_member_ids, outsider)

    def test_create_next_sprint(self):
        sprint = self._create_sprint(self.team_alpha, date(2030, 1, 1), date(2030, 1, 14))
        sprint.action_start()
        action = sprint.action_create_next_sprint()
        next_sprint = self.env['project.sprint'].browse(action['res_id'])
        self.assertEqual(next_sprint.team_id, self.team_alpha)
        self.assertEqual(next_sprint.date_start, date(2030, 1, 15))
        self.assertEqual(next_sprint.date_end, date(2030, 1, 28))
        self.assertEqual(next_sprint.name, 'Test Alpha - Sprint 2')
