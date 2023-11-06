import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def create_graph(data, x_value, y_value, x_label, y_label, title='Main', kind='bar', ax=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(15, 5))
    plot_func = sns.barplot if kind == 'bar' else sns.lineplot
    plot_func(data=data, x=x_value, y=y_value, ax=ax)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.tick_params(axis='x', rotation=45)


def get_u_by_date_and_hour(data):
    data['DATE'] = data['CUSTOM_SESSION_STARTED_AT'].dt.date
    data['HOUR'] = data['CUSTOM_SESSION_STARTED_AT'].dt.hour
    u_by_date = data.groupby('DATE')['RIDER_ID'].nunique().reset_index()
    u_by_hours = data.groupby('HOUR')['RIDER_ID'].count().reset_index()
    return u_by_date, u_by_hours


def c2p_metric(data):
    daily_c2p = pd.DataFrame({
        'calcs': data.groupby(data['DELIVERY_COST_CALCULATION_AT'].dt.date)['CUSTOM_SESSION_ID'].nunique(),
        'orders': data.groupby(data['DELIVERY_ORDER_PLACED_AT'].dt.date)['CUSTOM_SESSION_ID'].nunique()
    }).fillna(0)

    daily_c2p['C2P'] = round(((daily_c2p['orders'] / daily_c2p['calcs']) * 100), 2)
    daily_c2p = daily_c2p[daily_c2p['calcs'] > 1]
    return daily_c2p.reset_index().rename(columns={'index': 'date'})


def set_following_steps_null(row):
    if pd.isna(row['DELIVERY_COST_CALCULATION_AT']):
        row['DELIVERY_RECIPIENT_INFO_SCREEN_AT'] = None
        row['DELIVERY_RECIPIENT_INFO_SUCCESS_AT'] = None
        row['DELIVERY_ORDER_PLACED_AT'] = None
    return row


def count_selected(row):
    return not pd.isna(row['DELIVERY_PICK_UP_SELECTED_AT']) or not pd.isna(row['DELIVERY_DROP_OFF_SELECTED_AT'])


def anal_funnel(data):
    adjusted_funnel_steps = {
        'Type Screen': 'DELIVERY_TYPE_SCREEN_AT',
        'Selected': count_selected,
        'Calculation': 'DELIVERY_COST_CALCULATION_AT',
        'Recipient': 'DELIVERY_RECIPIENT_INFO_SCREEN_AT',
        'Recipient-Success': 'DELIVERY_RECIPIENT_INFO_SUCCESS_AT',
        'Order Placed': 'DELIVERY_ORDER_PLACED_AT'
    }
    df = data.apply(set_following_steps_null, axis=1)
    df = df[df['CUSTOM_SESSION_START_WITH'] == 'session_start']
    funnel_counts = {}
    for step, condition in adjusted_funnel_steps.items():
        if callable(condition):
            funnel_counts[step] = int(df.apply(condition, axis=1).sum().item())
        else:
            funnel_counts[step] = int(df[condition].notna().sum().item())
    return pd.DataFrame(list(funnel_counts.items()), columns=['step', 'count'])


def main():
    datetime_columns = [
        'CUSTOM_SESSION_STARTED_AT', 'DELIVERY_TYPE_SCREEN_AT', 'DELIVERY_COST_CALCULATION_AT',
        'DELIVERY_PICK_UP_SELECTED_AT', 'DELIVERY_DROP_OFF_SELECTED_AT', 'DELIVERY_RECIPIENT_INFO_SCREEN_AT',
        'DELIVERY_RECIPIENT_INFO_SUCCESS_AT', 'DELIVERY_ORDER_PLACED_AT'
    ]
    fig, axs = plt.subplots(4, 1, figsize=(15, 10))
    df = pd.read_csv('RIDER_FUNNEL_DELIVERY.csv')

    for col in datetime_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce', format='ISO8601')

    sessions_by_funnel_step = anal_funnel(df)
    u_by_date, u_by_hours = get_u_by_date_and_hour(df)
    df_c2p = c2p_metric(df)

    create_graph(u_by_date, 'DATE', 'RIDER_ID', 'date', 'users', 'DAU', kind='line', ax=axs[0])
    create_graph(u_by_hours, 'HOUR', 'RIDER_ID', 'hour', 'users', 'Users by hours', kind='bar', ax=axs[1])
    create_graph(df_c2p, 'date', 'C2P', 'date', '%C2P', 'C2P', kind='bar', ax=axs[2])
    create_graph(sessions_by_funnel_step, 'step', 'count', 'step', 'count', 'Funnel Anal', kind='bar', ax=axs[3])

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
