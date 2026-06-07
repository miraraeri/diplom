import csv

from django.contrib.auth import authenticate, login          # <-- обязательно
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied          # <-- добавьте, если используется raise PermissionDenied
from django.db.models import Q, Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse                              # <-- обязательно
from django.utils import timezone
from datetime import timedelta

from .models import *
from .forms import *
from .utils import *


# Вспомогательная функция создания уведомления
def create_notification(user, message, link=''):
    Notification.objects.create(user=user, message=message, link=link)


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

    # Поиск
    search = request.GET.get('search')
    if search:
        bids = bids.filter(
            Q(problem_text__icontains=search) |
            Q(employee__lastname__icontains=search) |
            Q(employee__firstname__icontains=search) |
            Q(employee__middlename__icontains=search) |
            Q(accepted_by__lastname__icontains=search) |
            Q(accepted_by__firstname__icontains=search) |
            Q(accepted_by__middlename__icontains=search)
        )

    # Фильтр по статусу
    status = request.GET.get('status')
    if status:
        bids = bids.filter(status=status)

    # Фильтр по дате создания
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        bids = bids.filter(time_create__date__gte=date_from)
    if date_to:
        bids = bids.filter(time_create__date__lte=date_to)

    # Фильтр по дате изменения
    update_from = request.GET.get('update_from')
    update_to = request.GET.get('update_to')
    if update_from:
        bids = bids.filter(time_update__date__gte=update_from)
    if update_to:
        bids = bids.filter(time_update__date__lte=update_to)

    bids = bids.order_by('-time_create')
    paginator = Paginator(bids, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    base_params = get_params.urlencode()

    status_choices = Bids.STATUSES

    context = {
        'title': 'Все заявки',
        'heading': 'Все заявки',
        'bids': page_obj,
        'base_params': base_params,
        'is_admin': user_role == 'Администратор',
        'is_sysadmin': user_role == 'Системный администратор',
        'is_user': user_role == 'Пользователь',
        'status_choices': status_choices,
    }
    return render(request, 'uchet/all_bids.html', context=context)


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

    if request.method == 'POST' and 'status_btn' in request.POST:
        if user_role == 'Системный администратор' and not is_owner:
            if bid.status == 'new':
                bid.status = 'in_progress'
                bid.accepted_at = timezone.now()
                bid.accepted_by = user
                bid.save()

                # Создаём или получаем чат
                chat, _ = Chat.objects.get_or_create(bid=bid)
                chat.participants.add(bid.employee)
                chat.participants.add(user)
                ChatParticipant.objects.get_or_create(chat=chat, user=bid.employee)
                ChatParticipant.objects.get_or_create(chat=chat, user=user)

                create_notification(
                    bid.employee,
                    f'Ваша заявка №{bid.id} принята в работу системным администратором {user.lastname} {user.firstname} {user.middlename or ""}',
                    reverse('chat_room', args=[chat.id])
                )
                messages.success(request, 'Заявка принята в работу')
            elif bid.status == 'in_progress':
                bid.status = 'done'
                bid.completed_at = timezone.now()
                bid.completed_by = user
                bid.save()
                create_notification(
                    bid.employee,
                    f'Ваша заявка №{bid.id} завершена',
                    reverse('show_bid', args=[bid.id])
                )
                messages.success(request, 'Заявка закрыта')
            return redirect('show_bid', bid_id=bid_id)

    employee_fullname = f'{bid.employee.lastname} {bid.employee.firstname} {bid.employee.middlename or ""}'

    # === Гарантируем существование чата ===
    chat = Chat.objects.filter(bid=bid).first()
    if not chat:
        chat = Chat.objects.create(bid=bid)
        chat.participants.add(bid.employee)
        ChatParticipant.objects.create(chat=chat, user=bid.employee)
        if bid.accepted_by:
            chat.participants.add(bid.accepted_by)
            ChatParticipant.objects.get_or_create(chat=chat, user=bid.accepted_by)

    context = {
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
        'chat': chat,
    }
    return render(request, 'uchet/show_bid.html', context=context)


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
    content = {'title': 'Подтверждение', 'bid': bid}
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
            # Создаём чат и добавляем автора
            chat = Chat.objects.create(bid=bid)
            chat.participants.add(request.user)
            ChatParticipant.objects.create(chat=chat, user=request.user)
            messages.success(request, 'Вы создали новую заявку')
            return redirect('all_bids')
    else:
        form = CreateBidForm()
    content = {'title': 'Создание', 'form': form}
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
    content = {'title': 'Изменение заявки', 'form': form, 'bid': bid}
    return render(request, 'uchet/edit_bid.html', context=content)


@login_required
@role_required(['Администратор', 'Системный администратор'])
def all_components(request):
    all_types = Types.objects.all()
    components = Components.objects.all()

    user = request.user
    user_role = user.role.name

    search = request.GET.get('search')
    if search:
        components = components.filter(
            Q(model__icontains=search) |
            Q(type__name__icontains=search)
        )

    type_id = request.GET.get('type')
    if type_id:
        components = components.filter(type_id=type_id)

    sort = request.GET.get('sort')
    if sort == 'asc':
        components = components.order_by('counts')
    elif sort == 'desc':
        components = components.order_by('-counts')
    else:
        components = components.order_by('model')

    paginator = Paginator(components, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    base_params = get_params.urlencode()

    context = {
        'title': 'Все комплектующие',
        'heading': 'Все комплектующие',
        'components': page_obj,
        'base_params': base_params,
        'types': all_types,
        'form': ComponentFilterForm(),
        'is_admin': user_role == 'Администратор',
    }
    return render(request, 'uchet/all_components.html', context)


@login_required
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
                # Уведомление для администраторов
                admins = User.objects.filter(role__name='Администратор')
                for admin in admins:
                    create_notification(
                        admin,
                        f'Списано {counts} шт. {component.model} ({component.type.name}) пользователем {request.user.lastname} {request.user.firstname} {request.user.middlename or ""}',
                        reverse('transaction_history')
                    )
                messages.success(request, f'Списано {counts} шт.')
            else:
                messages.error(request, 'Нельзя убрать больше, чем есть на складе')
        except ValueError:
            messages.error(request, 'Введите корректное количество')
    return redirect('all_components')


# ================== СТАТИСТИКА ==================
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

    top_accepted = (Bids.objects
                    .filter(accepted_by__isnull=False)
                    .values('accepted_by__lastname', 'accepted_by__firstname')
                    .annotate(cnt=Count('id'))
                    .order_by('-cnt')[:5])

    top_completed = (Bids.objects
                     .filter(completed_by__isnull=False)
                     .values('completed_by__lastname', 'completed_by__firstname')
                     .annotate(cnt=Count('id'))
                     .order_by('-cnt')[:5])

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

    accepted_daily = (Bids.objects
                      .filter(accepted_at__gte=last_30_days)
                      .annotate(date=TruncDate('accepted_at'))
                      .values('date')
                      .annotate(count=Count('id'))
                      .order_by('date'))
    accepted_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in accepted_daily}

    completed_daily = (Bids.objects
                       .filter(completed_at__gte=last_30_days)
                       .annotate(date=TruncDate('completed_at'))
                       .values('date')
                       .annotate(count=Count('id'))
                       .order_by('date'))
    completed_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in completed_daily}

    dates = [(timezone.now() - timedelta(days=i)).date() for i in range(30, -1, -1)]
    chart_labels = [d.strftime('%Y-%m-%d') for d in dates]
    accepted_counts = [accepted_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]
    completed_counts = [completed_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]

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

    # ------------------- РАЗДЕЛ ДЛЯ СИСТЕМНОГО АДМИНИСТРАТОРА -------------------
    if user_role == 'Системный администратор':
        my_accepted_count = Bids.objects.filter(accepted_by=user).count()
        my_completed_count = Bids.objects.filter(completed_by=user).count()

        handled_bids = Bids.objects.filter(Q(accepted_by=user) | Q(completed_by=user))
        bids_by_department = (handled_bids
                              .values('employee__department__name')
                              .annotate(cnt=Count('id'))
                              .order_by('-cnt')[:5])

        # 1. Динамика принятых и завершённых за последние 30 дней (для сисадмина)
        my_accepted_qs = Bids.objects.filter(
            accepted_by=user,
            accepted_at__gte=last_30_days,
            accepted_at__isnull=False
        ).annotate(date=TruncDate('accepted_at')).values('date').annotate(cnt=Count('id'))
        my_accepted_dict = {item['date'].strftime('%Y-%m-%d'): item['cnt'] for item in my_accepted_qs}
        my_accepted_counts = [my_accepted_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]

        my_completed_qs = Bids.objects.filter(
            completed_by=user,
            completed_at__gte=last_30_days,
            completed_at__isnull=False
        ).annotate(date=TruncDate('completed_at')).values('date').annotate(cnt=Count('id'))
        my_completed_dict = {item['date'].strftime('%Y-%m-%d'): item['cnt'] for item in my_completed_qs}
        my_completed_counts = [my_completed_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]

        # 2. Статусы заявок, которые обрабатывал текущий сисадмин (принимал или завершал)
        my_status_stats = {
            'in_progress': handled_bids.filter(status='in_progress').count(),
            'done': handled_bids.filter(status='done').count(),
        }
        my_total_handled = my_status_stats['in_progress'] + my_status_stats['done']
        if my_total_handled > 0:
            my_in_progress_percent = round(my_status_stats['in_progress'] / my_total_handled * 100, 1)
            my_done_percent = round(my_status_stats['done'] / my_total_handled * 100, 1)

        my_status_labels = [
            f"В работе ({my_in_progress_percent}%)",
            f"Завершённые ({my_done_percent}%)"
        ]

        # 3. Топ-5 сотрудников, для которых сисадмин принимал заявки
        my_top_employees = Bids.objects.filter(accepted_by=user).values(
            'employee__lastname', 'employee__firstname'
        ).annotate(cnt=Count('id')).order_by('-cnt')[:5]

        context = {
            'title': 'Моя статистика',
            'heading': 'Моя статистика',
            'user_role': user_role,
            'my_accepted_count': my_accepted_count,
            'my_completed_count': my_completed_count,
            'bids_by_department': bids_by_department,
            # Новые данные для графиков
            'my_chart_labels': chart_labels,
            'my_accepted_counts': my_accepted_counts,
            'my_completed_counts': my_completed_counts,
            'my_status_stats': my_status_stats,
            'my_status_labels': my_status_labels,
            'my_top_employees': my_top_employees,
        }
        return render(request, 'uchet/statistics.html', context)

    # ------------------- РАЗДЕЛ ДЛЯ АДМИНИСТРАТОРА -------------------
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


# ================== НОВЫЕ ПРЕДСТАВЛЕНИЯ ==================
@login_required
@role_required(['Администратор'])
def transaction_history(request):
    transactions = ComponentTransaction.objects.select_related('component__type', 'user').all()

    search = request.GET.get('search')
    if search:
        transactions = transactions.filter(
            Q(user__lastname__icontains=search) |
            Q(user__firstname__icontains=search) |
            Q(user__middlename__icontains=search) |
            Q(component__model__icontains=search)
        )

    type_id = request.GET.get('type')
    if type_id:
        transactions = transactions.filter(component__type_id=type_id)

    qty_from = request.GET.get('qty_from')
    qty_to = request.GET.get('qty_to')
    if qty_from:
        transactions = transactions.filter(quantity__gte=qty_from)
    if qty_to:
        transactions = transactions.filter(quantity__lte=qty_to)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        transactions = transactions.filter(taken_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(taken_at__date__lte=date_to)

    transactions = transactions.order_by('-taken_at')
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    base_params = get_params.urlencode()

    types = Types.objects.all()

    context = {
        'title': 'История списаний',
        'heading': 'История списаний',
        'transactions': page_obj,
        'types': types,
        'base_params': base_params,
    }
    return render(request, 'uchet/transaction_history.html', context)


@login_required
def get_notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    data = [{
        'id': n.id,
        'message': n.message,
        'link': n.link,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M')
    } for n in notifs]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread_count': unread_count})


@login_required
def mark_notification_read(request, notif_id):
    if request.method == 'POST':
        notif = get_object_or_404(Notification, id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def get_unread_chat_count(request):
    user = request.user
    total_unread = 0
    parts = ChatParticipant.objects.filter(user=user).select_related('chat')
    for part in parts:
        chat = part.chat
        last_read = part.last_read_message
        if last_read:
            unread = chat.message_set.filter(created_at__gt=last_read.created_at).exclude(sender=user).count()
        else:
            unread = chat.message_set.exclude(sender=user).count()
        total_unread += unread
    display = str(total_unread) if total_unread <= 10 else '10+'
    return JsonResponse({'unread_count': total_unread, 'display': display})


@login_required
def chat_list(request):
    user = request.user
    parts = ChatParticipant.objects.filter(user=user).select_related('chat__bid')
    chats_with_unread = []
    for part in parts:
        chat = part.chat
        last_read = part.last_read_message
        if last_read:
            unread = chat.message_set.filter(created_at__gt=last_read.created_at).exclude(sender=user).count()
        else:
            unread = chat.message_set.exclude(sender=user).count()
        chats_with_unread.append({'chat': chat, 'unread': unread})

    context = {
        'title': 'Мои чаты',
        'chats_with_unread': chats_with_unread,
    }
    return render(request, 'uchet/chat_list.html', context)


@login_required
def chat_room(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    user = request.user
    if not chat.participations.filter(user=user).exists():
        raise PermissionDenied

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Message.objects.create(chat=chat, sender=user, text=text)
        return redirect('chat_room', chat_id=chat.id)

    # Пометить как прочитанное
    last_msg = chat.message_set.last()
    if last_msg:
        participation = chat.participations.get(user=user)
        participation.last_read_message = last_msg
        participation.save()

    chat_messages = chat.message_set.order_by('created_at')   # ← переименовано
    context = {
        'title': f'Чат заявки №{chat.bid.id}',
        'chat': chat,
        'chat_messages': chat_messages,                       # ← новое имя
    }
    return render(request, 'uchet/chat_room.html', context)


def about(request):
    context = {
        'title': 'О системе',
        'heading': 'О системе HelpDesk',
    }
    return render(request, 'uchet/about.html', context)


# Экспорты
def export_bids_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bids_export.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['ID', 'Проблема', 'Сотрудник', 'Статус', 'Создано', 'Обновлено', 'Решение'])
    bids = Bids.objects.select_related('employee')
    for b in bids:
        writer.writerow([
            b.id, b.problem_text,
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
    return redirect('about')


def pageNotFound(request, exception):
    context = {'menu': [], 'title': 'Страница не найдена', 'heading': '', 'user': request.user}
    return render(request, 'uchet/404.html', context=context, status=404)


def permission_denied(request, exception):
    context = {'menu': [], 'title': 'Доступ запрещён', 'heading': '', 'user': request.user}
    return render(request, 'uchet/403.html', context=context, status=403)