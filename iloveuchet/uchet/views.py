import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from .forms import *
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .utils import *
from django.core.paginator import Paginator
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.utils import timezone


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
        'hide_login_button': True,
        'hide_footer': True
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

    paginator = Paginator(bids, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    base_params = get_params.urlencode()

    bids_content = {
        'title': 'Все заявки',
        'heading': 'Все заявки',
        'bids': page_obj,
        'form': form,
        'base_params': base_params,
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
            bid.accepted_at = timezone.now()
            bid.accepted_by = user
            messages.success(request, 'Заявка принята в работу')
        elif bid.status == 'in_progress':
            bid.status = 'done'
            bid.completed_at = timezone.now()
            bid.completed_by = user
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
@role_required(['Системный администратор'])
def edit_resolution(request, bid_id):
    bid = get_object_or_404(Bids, pk=bid_id)

    if request.method == 'POST':
        form = ResolutionForm(request.POST, instance=bid)
        if form.is_valid():
            form.save()
            messages.success(request, 'Решение сохранено')
            return redirect('show_bid', bid_id=bid.id)
    else:
        form = ResolutionForm(instance=bid)
    return render(request, 'uchet/edit_resolution.html', {'form': form, 'bid': bid})


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

    paginator = Paginator(components, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    base_params = get_params.urlencode()

    components_content = {
        'title': 'Все комплектующие',
        'heading': 'Все комплектующие',
        'components': page_obj,
        'base_params': base_params,
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

                ComponentTransaction.objects.create(
                    component=component,
                    user=request.user,
                    quantity=counts,
                    comment=request.POST.get('comment', '')
                )
                messages.success(request, f'Списано {counts} шт.')
            else:
                messages.error(request, 'Нельзя убрать больше, чем есть на складе')
        except ValueError:
            messages.error(request, 'Введите корректное количество')
        return redirect('all_components')
    return redirect('all_components')


@login_required()
@role_required(['Администратор', 'Системный администратор'])
def statistics_view(request):
    user = request.user
    user_role = user.role.name

    total_bids = Bids.objects.count()
    new_bids = Bids.objects.filter(status='new').count()
    in_progress_bids = Bids.objects.filter(status='in_progress').count()
    done_bids = Bids.objects.filter(status='done').count()

    bids_by_department = (Bids.objects
                          .values('employee__department__name')
                          .annotate(cnt=Count('id'))
                          .order_by('-cnt')[:5])

    # Топ системных администраторов по принятым заявкам
    top_accepted = (Bids.objects
                    .filter(accepted_by__isnull=False)
                    .values('accepted_by__lastname', 'accepted_by__firstname')
                    .annotate(cnt=Count('id'))
                    .order_by('-cnt')[:5])

    # Топ системных администраторов по завершённым заявкам
    top_completed = (Bids.objects
                     .filter(completed_by__isnull=False)
                     .values('completed_by__lastname', 'completed_by__firstname')
                     .annotate(cnt=Count('id'))
                     .order_by('-cnt')[:5])

    # Динамика за последние 30 дней (для линейного графика)
    last_30_days = timezone.now() - timedelta(days=30)
    bids_daily_qs = (Bids.objects
                     .filter(time_create__gte=last_30_days)
                     .annotate(date=TruncDate('time_create'))
                     .values('date')
                     .annotate(count=Count('id'))
                     .order_by('date'))

    daily_data = [
        {'date': item['date'].strftime('%Y-%m-%d'), 'count': item['count']}
        for item in bids_daily_qs
    ]

    # Принятые по дням
    accepted_daily = (Bids.objects
                      .filter(accepted_at__gte=last_30_days)
                      .annotate(date=TruncDate('accepted_at'))
                      .values('date')
                      .annotate(count=Count('id'))
                      .order_by('date'))
    accepted_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in accepted_daily}

    # Завершённые по дням
    completed_daily = (Bids.objects
                       .filter(completed_at__gte=last_30_days)
                       .annotate(date=TruncDate('completed_at'))
                       .values('date')
                       .annotate(count=Count('id'))
                       .order_by('date'))
    completed_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in completed_daily}

    # Список всех дат за 30 дней
    dates = [(timezone.now() - timedelta(days=i)).date() for i in range(30, -1, -1)]
    chart_labels = [d.strftime('%Y-%m-%d') for d in dates]
    accepted_counts = [accepted_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]
    completed_counts = [completed_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]

    # Для круговой диаграммы
    status_stats = {
        'new': new_bids,
        'in_progress': in_progress_bids,
        'done': done_bids,
    }

    total = status_stats['new'] + status_stats['in_progress'] + status_stats['done']
    if total > 0:
        new_percent = round(status_stats['new'] / total * 100, 1)
        in_progress_percent = round(status_stats['in_progress'] / total * 100, 1)
        done_percent = round(status_stats['done'] / total * 100, 1)
    else:
        new_percent = in_progress_percent = done_percent = 0

    status_labels_with_percent = [
        f"Новые ({new_percent}%)",
        f"В работе ({in_progress_percent}%)",
        f"Завершённые ({done_percent}%)"
    ]

    transactions = ComponentTransaction.objects.select_related('component', 'user').order_by('-taken_at')[:20]
    total_components = Components.objects.aggregate(total=Sum('counts'))['total'] or 0
    low_stock_components = Components.objects.filter(counts__lt=5).count()

    if user_role == 'Системный администратор':
        # Персональная статистика для сисадмина
        my_accepted_count = Bids.objects.filter(accepted_by=user).count()
        my_completed_count = Bids.objects.filter(completed_by=user).count()

        # Заявки, которые он обрабатывал (принял или завершил)
        handled_bids = Bids.objects.filter(Q(accepted_by=user) | Q(completed_by=user))
        bids_by_department = (handled_bids
                              .values('employee__department__name')
                              .annotate(cnt=Count('id'))
                              .order_by('-cnt')[:5])

        context = {
            'title': 'Моя статистика',
            'heading': 'Моя статистика',
            'user_role': user_role,
            'my_accepted_count': my_accepted_count,
            'my_completed_count': my_completed_count,
            'bids_by_department': bids_by_department,
        }
        return render(request, 'uchet/statistics.html', context)

    context = {
        'title': 'Статистика',
        'heading': 'Статистика и отчёты',
        'total_bids': total_bids,
        'new_bids': new_bids,
        'in_progress_bids': in_progress_bids,
        'done_bids': done_bids,
        'bids_by_department': bids_by_department,
        'daily_data': daily_data,
        'top_accepted': top_accepted,
        'top_completed': top_completed,
        'chart_labels': chart_labels,
        'accepted_counts': accepted_counts,
        'completed_counts': completed_counts,
        'status_stats': status_stats,
        'status_labels_with_percent': status_labels_with_percent,
        'transactions': transactions,
        'total_components': total_components,
        'low_stock_components': low_stock_components,

        'user_role': user_role,
    }
    return render(request, 'uchet/statistics.html', context)


def export_bids_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bids_export.csv"'
    response.write('\ufeff')  # BOM для Excel
    writer = csv.writer(response)
    writer.writerow(['ID', 'Проблема', 'Сотрудник', 'Статус', 'Создано', 'Обновлено', 'Решение'])
    bids = Bids.objects.select_related('employee')
    for b in bids:
        writer.writerow([
            b.id,
            b.problem_text,
            f"{b.employee.lastname} {b.employee.firstname} {b.employee.middlename or ''}",
            b.get_status_display(),
            b.time_create.strftime('%Y-%m-%d %H:%M'),
            b.time_update.strftime('%Y-%m-%d %H:%M'),
            b.resolution or ''
        ])
    return response


def export_transactions_csv(request):
    if request.user.role.name != 'Администратор':
        raise PermissionDenied
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="components_transactions.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Комплектующее', 'Взял(а)', 'Количество', 'Дата', 'Примечание'])
    transactions = ComponentTransaction.objects.select_related('component', 'user')
    for t in transactions:
        writer.writerow([
            t.component.model,
            f"{t.user.lastname} {t.user.firstname} {t.user.middlename or ''}",
            t.quantity,
            t.taken_at.strftime('%Y-%m-%d %H:%M'),
            t.comment
        ])
    return response


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
