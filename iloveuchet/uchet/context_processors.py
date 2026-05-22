def menu(request):
    menu_items = []

    if request.user.is_authenticated:
        user_role = request.user.role.name

        if user_role == 'Администратор':
            menu_items.append({'title': 'АдминПанель', 'url_name': 'admin:index'})
            menu_items.append({'title': 'Комплектующие', 'url_name': 'all_components'})
        elif user_role == 'Системный администратор':
            menu_items.append({'title': 'Комплектующие', 'url_name': 'all_components'})

        menu_items.append({'title': 'Заявки', 'url_name': 'all_bids'})

    menu_items.append({'title': 'Инструкция', 'url_name': 'instruction'},)

    return {'menu': menu_items}
