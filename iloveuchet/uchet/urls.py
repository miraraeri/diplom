from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import *

urlpatterns = [
    path('all_bids/', all_bids, name='all_bids'),
    path('', instruction, name='instruction'),
    path('instruction/', instruction, name='instruction'),
    path('all_components/', all_components, name='all_components'),
    path('show_bid/<int:bid_id>/', show_bid, name='show_bid'),
    path('create_bid/', create_bid, name='create_bid'),
    path('component/counts/remove/<int:component_id>/', remove_from_storage, name='remove_from_storage'),
    path('login/', auth, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('bid/<int:bid_id>/delete/', confirm_delete_bid, name='confirm_delete_bid'),
    path('bid/<int:bid_id>/delete/done/', delete_bid, name='delete_bid'),
    path('edit_bid/<int:bid_id>', edit_bid, name='edit_bid'),
    path('bid/<int:bid_id>/edit-resolution/', edit_resolution, name='edit_resolution'),
    path('statistics/', statistics_view, name='statistics'),
    path('export/bids/', export_bids_csv, name='export_bids_csv'),
    path('export/transactions/', export_transactions_csv, name='export_transactions_csv')
]
