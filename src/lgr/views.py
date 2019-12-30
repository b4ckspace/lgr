from json import loads
from itertools import chain
from django.contrib.auth import authenticate, login, logout
from django.db import models as fancy
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import redirect

from lgr import models


@ensure_csrf_cookie
def index(request): # pylint: disable=unused-argument
    """Index view."""
    return redirect('/static/index.html?#')


@ensure_csrf_cookie
def auth(request):
    """Auth view."""
    if request.method == 'DELETE':
        logout(request)

    elif request.method == 'POST' and request.content_type == 'application/json':
        payload = loads(request.body.decode())
        user = authenticate(**payload)
        if user and user.is_authenticated:
            login(request, user)
        else:
            response = {
                'logged_in': False,
                'username': '',
                'message': 'Invalid password or username.'
            }
            return JsonResponse(response, status=400)

    if request.user and request.user.is_authenticated:
        response = {
            'logged_in': True,
            'username': request.user.username
        }
        return JsonResponse(response)

    response = {'logged_in': False, 'username': ''}
    return JsonResponse(response)


def loan(request):
    """Loan view."""

    # validatioin
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Not logged in.'}, status=401)
    if request.method != 'POST' or request.content_type != 'application/json':
        return JsonResponse({'message': 'Invalid request.'}, status=400)

    payload = loads(request.body.decode())
    return_date = payload['return_date']
    preview = payload.get('preview', False)
    items = payload['items']
    items = [i['code'] for i in items]
    items = models.Barcode.objects.filter(code__in=items)

    # resolve children if preview
    if preview:
        items = chain.from_iterable(item.all_children for item in items)

    # query if any of them is loan
    is_loan = fancy.Count('loans', filter=fancy.Q(loans__status=models.Loan.TAKEN))
    items_info = (
        models.Barcode.objects
        .filter(code__in=[c.code for c in items])
        .values('code', 'description', 'item__name')
        .annotate(is_loan=is_loan)
    )

    # preview
    if preview:
        barcodes = []
        blocked = []
        for i in items_info:
            link = blocked if i['is_loan'] else barcodes
            link.append({
                'code': i['code'],
                'loan': bool(i['is_loan']),
                'person': (
                    models.Loan.objects.filter(
                        status=models.Loan.TAKEN,
                        barcodes__code=i['code']
                    ).first().person.nickname
                    if bool(i['is_loan'])
                    else ''
                ),
                'item_name': i['item__name'],
                'description': i['description'],
            })

        return JsonResponse({'items': barcodes, 'blocked': blocked})


    # invalid loan
    loan_items = [i for i in items_info if i['is_loan']]
    if loan_items:
        response = {'messsage': 'Some barcodes are already loan.',}
        return JsonResponse(response, status=400)

    # valid loan
    person = models.Person.objects.get(nickname=request.user.username)
    _loan = models.Loan.objects.create(person=person, return_date=return_date)
    _loan.barcodes.set(items.all())
    response = {'message': 'Loan for %s items created.' % _loan.barcodes.count()}
    return JsonResponse(response)
