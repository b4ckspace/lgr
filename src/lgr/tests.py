from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import JsonResponse
from json import loads

from lgr import models
from lgr import admin

class MainTestCase(TestCase):

    def setUp(self):
        self.maxDiff = None

        self.backspace = models.Person.objects.create(
            nickname='backspace',
            firstname='Backspace',
            lastname='Bamberg',
            email='hackerspace@localhost.local'
        )
        self.guy = models.Person.objects.create(
            nickname='Max',
            firstname='Max',
            lastname='Mustermann',
            email='max@mustermann.de'
        )
        self.test_admin = models.Person.objects.create(
            nickname='test_admin',
            firstname='test',
            lastname='admin',
            email='admin@local.lan'
        )
        self.cool = models.Tag.objects.create(name='Cool')
        self.fancy = models.Tag.objects.create(name='Fancy')
        self.tool = models.Item.objects.create(name='Triangle', description='!!')
        self.tool = models.Item.objects.create(name='Square', description='!!!')
        self.tool = models.Item.objects.create(name='Hexagon', description='!!!!')
        self.tool = models.Item.objects.create(name='Circle', description='!!!!!')
        self.barcodes = list()
        for i in ['1335', '1336', '1337']:
            barcode = models.Barcode.objects.create(
                code=i,
                owner=self.backspace,
                item=self.tool,
            )
            self.barcodes.append(barcode)

        self.username = "test_admin"
        self.password = User.objects.make_random_password()
        user, _ = User.objects.get_or_create(username=self.username)
        user.set_password(self.password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        self.user = user
        self.client.login(username=self.username, password=self.password)

    def test_barcode_quickadd_validate(self):
        """Test adding of barcodes"""
        from lgr.validators import barcode_quickadd, BarcodeTuple

        l = barcode_quickadd(
            '1234:Triangle\n'
            '--1235:Hexagon\n'
            '----1236:Square:4 Ecken\n'
            '1237:Circle\n'
            '1337\n'
            '  1238:Circle\n'
            '# foosinn\n'
            '7777:CreateItemTest\n'
        )
        l_should = [
            BarcodeTuple(code='1234', item='Triangle', parent=None,
                         owner=self.backspace, description=''),
            BarcodeTuple(code='1235', item='Hexagon', parent='1234',
                         owner=self.backspace, description=''),
            BarcodeTuple(code='1236', item='Square', parent='1235',
                         owner=self.backspace, description='4 Ecken'),
            BarcodeTuple(code='1237', item='Circle', parent=None,
                         owner=self.backspace, description=''),
            BarcodeTuple(code='1238', item='Circle', parent='1337',
                         owner=self.backspace, description=''),
            BarcodeTuple(code='7777', item='CreateItemTest', parent=None,
                         owner='foosinn', description=''),
        ]
        self.assertEqual(l, l_should)

        from django.core.exceptions import ValidationError

        # malformated line
        with self.assertRaises(ValidationError):
            barcode_quickadd('#backspace\nuseless line')

        # more than one indentation added inbetween
        with self.assertRaises(ValidationError):
            barcode_quickadd('#backspace\n----1234:over indent')

        # more than one indentation added inbetween
        with self.assertRaises(ValidationError):
            barcode_quickadd('#backspace\n1337\n7778:--tester\n------1234:over indent')

        # wrong indent
        with self.assertRaises(ValidationError):
            barcode_quickadd('#backspace\n-wrong indent')

        # alread known barcode
        with self.assertRaises(ValidationError):
            barcode_quickadd('#backspace\n1337:already known')

        # missing data
        with self.assertRaises(ValidationError):
            barcode_quickadd('invalid\n')

        # check for missing seperation between barcode and item name
        with self.assertRaises(ValidationError):
            barcode_quickadd('# backspace\n900\n--12378235 Schraubstock')

    def test_index_view(self):
        """Test index view."""
        view = self.client.get(reverse('index'))
        self.assertEqual(view.status_code, 302)

    def test_auth_view(self):
        """Test auth view for frontend."""
        self.client.logout()

        # check login status (logged out)
        view = self.client.get(reverse('auth'))
        self.assertIsInstance(view, JsonResponse)
        self.assertJSONEqual(view.content, {'logged_in': False, 'username': ''})

        # login
        view = self.client.post(
            reverse('auth'),
            {'username': self.username, 'password': self.password},
            content_type='application/json',
        )
        self.assertIsInstance(view, JsonResponse)
        self.assertJSONEqual(view.content, {'logged_in': True, 'username': 'test_admin'})

        # check login status (logged in)
        view = self.client.get(reverse('auth'))
        self.assertIsInstance(view, JsonResponse)
        self.assertJSONEqual(view.content, {'logged_in': True, 'username': 'test_admin'})

        # logout
        view = self.client.delete(reverse('auth'))
        self.assertIsInstance(view, JsonResponse)
        self.assertJSONEqual(view.content, {'logged_in': False, 'username': ''})

        # invalid login
        view = self.client.post(
            reverse('auth'),
            {'username': 'invalid', 'password': 'login'},
            content_type='application/json',
        )
        self.assertIsInstance(view, JsonResponse)
        self.assertJSONEqual(view.content, {
            'logged_in': False,
            'username': '',
            'message': 'Invalid password or username.'
        })

    def test_loan_view(self):
        """Test loan creation view for frontend."""
        view = self.client.get(reverse('loan'))
        self.assertEqual(view.status_code, 400)
        self.assertJSONEqual(view.content, {'message': 'Invalid request.'})

        view = self.client.post(
            reverse('loan'),
            {
                'return_date': '2018-12-25T23:00:00.000Z',
                'items':[{'code':'1335'}],
                'preview': True,
            },
            content_type='application/json',
        )
        self.assertEqual(view.status_code, 200)
        self.assertJSONEqual(view.content, {
            'blocked': [],
            'items': [
                {
                    'code': '1335',
                    'loan': False,
                    'person': '',
                    'item_name': 'Circle',
                    'description': ''
                }
            ]
        })

        self.client.logout()
        view = self.client.get(reverse('loan'))
        self.assertEqual(view.status_code, 401)
        self.assertJSONEqual(view.content, {'message': 'Not logged in.'})

    def test_barcode_admin_view(self):
        """Load admin site of Barcode to see if changes broke anything."""
        barcode_admin_view = self.client.get(reverse('admin:lgr_barcode_changelist'))
        self.assertEqual(barcode_admin_view.status_code, 200)

    def test_barcode_change_admin_view(self):
        """Load the barcodes change view."""
        barcode_change_admin_view = self.client.get(
            reverse('admin:lgr_barcode_change', args=[self.barcodes[0].pk])
        )
        self.assertEqual(barcode_change_admin_view.status_code, 200)

    def test_barcode_quickadd_admin_view(self):
        """Load admin site of Barcode/Quickadd to see if changes broke anything."""
        barcode_quickadd_admin_view = self.client.get(reverse('admin:lgr_barcode_quickadd'))
        self.assertEqual(barcode_quickadd_admin_view.status_code, 200)

    def test_barcode_quickadd_for_barcode_admin_view(self):
        """Load admin site of Barcode/Quickadd to see if changes broke anything."""
        barcode_quickadd_admin_view = self.client.get(
            reverse('admin:lgr_barcode_quickadd_for_barcode',
                    args=[self.barcodes[0].pk])
        )
        self.assertEqual(barcode_quickadd_admin_view.status_code, 200)

    def test_barcode_move_admin_view(self):
        """Load admin site of Barcode/Move and test."""
        barcode_move_admin_view = self.client.get(
            reverse('admin:lgr_barcode_move_for_barcode',
                    args=[self.barcodes[0].pk])
        )
        self.assertEqual(barcode_move_admin_view.status_code, 200)

    def test_item_admin_view(self):
        """Load admin site of Item to see if changes broke anything."""
        item_admin_view = self.client.get(reverse('admin:lgr_item_changelist'))
        self.assertEqual(item_admin_view.status_code, 200)

    def test_item_change_admin_view(self):
        """Load the items change view."""
        item_change_admin_view = self.client.get(
            reverse('admin:lgr_item_change', args=[self.barcodes[0].item.pk])
        )
        self.assertEqual(item_change_admin_view.status_code, 200)

    def test_loan_admin_view(self):
        """Load admin site of Loan to see if changes broke anything."""
        loan_admin_view = self.client.get(reverse('admin:lgr_loan_changelist'))
        self.assertEqual(loan_admin_view.status_code, 200)

    def test_loan_return_admin_view(self):
        """Create a Loan and return it partially. Check if new Loan gets created
        with the correct content."""
        # create loan
        loan = models.Loan.objects.create(person=self.guy)
        loan.barcodes.set(self.barcodes)
        loan.save()

        # test return view
        loan_return_admin_view = self.client.get(reverse('admin:lgr_loan_return',
                                                   args=[loan.id]))
        self.assertEqual(loan_return_admin_view.status_code, 200)

        # return partially
        loan_return_items = self.barcodes[:-1]
        loan_leftover_item = self.barcodes[-1]

        loan_return_admin_view = self.client.post(
            reverse('admin:lgr_loan_return', args=[loan.pk]),
            {
                'loan_pk': loan.pk,
                'items': [b.pk for b in loan_return_items],
                'comment': 'Test.',
            }
        )
        self.assertEqual(loan_return_admin_view.status_code, 302)

        # check the two loans
        loan.refresh_from_db()
        self.assertEqual(loan.status, 'returned')
        self.assertEqual(list(loan.barcodes.all()), loan_return_items)
        leftover_loan = models.Loan.objects.last()
        self.assertEqual(leftover_loan.status, 'taken')
        self.assertEqual(list(leftover_loan.barcodes.all()), [loan_leftover_item, ])

        loan_change_admin_view = self.client.get(
            reverse('admin:lgr_loan_change', args=[loan.pk])
        )
        self.assertEqual(loan_change_admin_view.status_code, 200)


    def test_person_admin_view(self):
        """Load admin site of Person to see if changes broke anything."""
        person_admin_view = self.client.get(reverse('admin:lgr_person_changelist'))
        self.assertEqual(person_admin_view.status_code, 200)

    def test_tag_admin_view(self):
        """Load admin site of Tag to see if changes broke anything."""
        tag_admin_view = self.client.get(reverse('admin:lgr_tag_changelist'))
        self.assertEqual(tag_admin_view.status_code, 200)

    def test_history_admin_view(self):
        """Load admin site of History to see if changes broke anything."""
        history_admin_view = self.client.get(reverse('admin:lgr_history_changelist'))
        self.assertEqual(history_admin_view.status_code, 200)
