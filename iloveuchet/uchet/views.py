from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.db.models.functions import Lower
from .forms import *
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .utils import *

# Create your views here.


def auth(request):
    if request.method == 'POST':
        form = AuthForm(request.POST)
        if form.is_valid():
            contacts = form.cleaned_data['contacts']
            password = form.cleaned_data['password']
            user = authenticate(request, contacts=contacts, password=password)
            if user is not None:
                if not user.is_active:
                    form.add_error(None, 'Учётная запись неактивна. Обратитесь к администратору.')
                else:
                    login(request, user)
                    return redirect('all_bids')
            else:
                form.add_error(None, 'Неверный телефон или пароль')
    else:
        form = AuthForm()
    content = {
        'title': 'Авторизация',
        'form': form,
        'hide_login_button': True
    }
    return render(request, 'uchet/auth.html', context=content)


@login_required
def all_bids(request):
    user = request.user
    user_role = user.role.name

    if user_role == 'Системный администратор':
        bids = Bids.objects.all()
    else:
        bids = Bids.objects.filter(employee=user)

    form = BidFilterForm(request.GET)
    if form.is_valid():
        status = form.cleaned_data.get('status')
        search = form.cleaned_data.get('search')

        if status:
            bids = bids.filter(status=status)

        if search:
            bids = bids.filter(
                Q(problem_text__icontains=search) |
                Q(employee__lastname__icontains=search) |
                Q(employee__firstname__icontains=search) |
                Q(employee__middlename__icontains=search)
            )

    bids_content = {
        'title': 'Все заявки',
        'heading': 'Все заявки',
        'bids': bids,
        'form': form,
        'is_admin': user_role == 'Администратор',
        'is_sysadmin': user_role == 'Системный администратор',
        'is_user': user_role == 'Пользователь',
    }
    return render(request, 'uchet/all_bids.html', context=bids_content)


@login_required
def show_bid(request, bid_id):
    bid = get_object_or_404(Bids, pk=bid_id)
    user = request.user
    user_role = user.role.name
    is_owner = (bid.employee == user)

    if not user_role == 'Системный администратор' and not is_owner:
        raise PermissionDenied

    btn_name = None
    if user_role == 'Системный администратор' and not is_owner:
        if bid.status == 'new':
            btn_name = 'Принять заявку'
        elif bid.status == 'in_progress':
            btn_name = 'Закрыть заявку'
        else:
            btn_name = 'Заявка закрыта'

    if request.method == 'POST' and user_role == 'Системный администратор' and not is_owner:
        if bid.status == 'new':
            bid.status = 'in_progress'
            messages.success(request, 'Заявка принята в работу')
        elif bid.status == 'in_progress':
            bid.status = 'done'
            messages.success(request, 'Заявка закрыта')
        bid.save()
        return redirect('show_bid', bid_id=bid_id)

    employee_fullname = f'{bid.employee.lastname} {bid.employee.firstname} {bid.employee.middlename}'

    bid_content = {
        'title': 'Заявка на техобслуживание',
        'heading': 'Заявка на техобслуживание',
        'bid': bid,
        'employee_fullname': employee_fullname,
        'user_role': user_role,
        'is_owner': is_owner,
        'btn_name': btn_name,
        'is_admin': user_role == 'Администратор',
        'is_sysadmin': user_role == 'Системный администратор',
        'is_user': user_role == 'Пользователь',
    }
    return render(request, 'uchet/show_bid.html', context=bid_content)


@login_required
def confirm_delete_bid(request, bid_id):
    bid = get_object_or_404(Bids, pk=bid_id)
    user = request.user
    is_owner = (bid.employee == user)

    if not is_owner:
        raise PermissionDenied("Вы не можете подтвердить удаление чужой заявки.")
    
    if bid.status != 'new':
        messages.error(request, 'Нельзя удалить заявку, которая уже в работе или завершена')
        return redirect('show_bid', bid_id=bid.id)

    content = {
        'title': 'Подтверждение',
        'bid': bid
    }
    return render(request, 'uchet/confirm_delete.html', context=content)


@login_required
def delete_bid(request, bid_id):
    bid = get_object_or_404(Bids, pk=bid_id)
    user = request.user
    is_owner = (bid.employee == user)

    if not is_owner:
        raise PermissionDenied("Вы не можете удалить чужую заявку.")

    if bid.status != 'new':
        messages.error(request, 'Нельзя удалить заявку, которая уже в работе или завершена')
        return redirect('show_bid', bid_id=bid.id)

    bid.delete()
    messages.success(request, f'Заявка №{bid_id} успешно удалена.')
    return redirect('all_bids')


@login_required
def create_bid(request):
    if request.method == 'POST':
        form = CreateBidForm(request.POST)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.status = 'new'
            bid.employee = request.user
            bid.save()
            messages.success(request, 'Вы создали новую заявку')
            return redirect('all_bids')
    else:
        form = CreateBidForm()
    content = {
        'title': 'Создание',
        'form': form
    }
    return render(request, 'uchet/new_bid.html', context=content)


@login_required
def edit_bid(request, bid_id):
    bid = get_object_or_404(Bids, pk=bid_id)
    user = request.user
    is_owner = (bid.employee == user)

    if not is_owner:
        raise PermissionDenied("Вы не можете редактировать чужую заявку.")

    if request.method == 'POST':
        form = CreateBidForm(request.POST, instance=bid)
        if form.is_valid():
            form.save()
            bid.refresh_from_db()
            messages.success(request, f'Заявка №{bid_id} успешно изменена.')
            return redirect('show_bid', bid_id=bid.id)
    else:
        form = CreateBidForm(instance=bid)
    content = {
        'title': 'Изменение заявки',
        'form': form,
        'bid': bid}
    return render(request, 'uchet/edit_bid.html', context=content)


@login_required()
@role_required(['Администратор', 'Системный администратор'])
def all_components(request):
    form = ComponentFilterForm(request.GET)
    components = Components.objects.all()

    if form.is_valid():
        search = form.cleaned_data.get('search')
        hardware = form.cleaned_data.get('hardware')

        if search:
            components = components.filter(
                Q(model__icontains=search) |
                Q(type__name__icontains=search) |
                Q(counts__icontains=search)
            )

        if hardware:
            components = components.filter(
                type__categories=hardware
            )

    components_content = {
        'title': 'Все комплектующие',
        'heading': 'Все комплектующие',
        'components': components,
        'form': form
    }
    return render(request, 'uchet/all_components.html', context=components_content)


@login_required()
@role_required(['Администратор', 'Системный администратор'])
def remove_from_storage(request, component_id):
    component = get_object_or_404(Components, pk=component_id)
    if request.method == 'POST':
        try:
            counts = int(request.POST.get('quantity', 0))
            if component.counts >= counts:
                component.counts -= counts
                component.save()
            else:
                messages.success(request, 'Нельзя убрать больше, чем есть на складе')
            return redirect('all_components')

        except Exception:
            messages.success(request, 'Введите количество комплектующих')
            return redirect('all_components')


def instruction(request):
    context = {
        'title': 'Инструкция',
        'heading': 'Инструкция пользователя',
    }
    return render(request, 'uchet/instruction.html', context=context)


def pageNotFound(request, exception):
    context = {
        'menu': [],
        'title': 'Страница не найдена',
        'heading': '',
        'user': request.user,
    }
    return render(request, 'uchet/404.html', context=context, status=404)


def permission_denied(request, exception):
    context = {
        'menu': [],
        'title': 'Доступ запрещён',
        'heading': '',
        'user': request.user,
    }
    return render(request, 'uchet/403.html', context=context, status=403)
