# Import Library
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency

import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static

sns.set(style='dark')

# Helper function yang dibutuhkan untuk menyiapkan berbagai dataframe
def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='order_purchase_timestamp').agg({
        "order_id": "nunique",
        "price": "sum"  # Assuming price is the total price
    })
    daily_orders_df = daily_orders_df.reset_index()
    daily_orders_df.rename(columns={
        "order_id": "order_count",
        "price": "revenue"
    }, inplace=True)
    return daily_orders_df

def create_sum_order_items_df(df):
    sum_order_items_df = df.groupby("product_id").price.sum().reset_index()  # Assuming quantity_x is represented by price here
    sum_order_items_df = sum_order_items_df.sort_values(by="price", ascending=False).reset_index()
    sum_order_items_df.rename(columns={"price": "total_sales"}, inplace=True)
    return sum_order_items_df

def create_rfm_df(df):
    rfm_df = df.groupby(by="customer_id", as_index=False).agg({
        "order_purchase_timestamp": "max",  
        "order_id": "nunique",
        "price": "sum"  
    })
    rfm_df.columns = ["customer_id", "max_order_timestamp", "frequency", "monetary"]
    
    rfm_df["max_order_timestamp"] = rfm_df["max_order_timestamp"].dt.date
    recent_date = df["order_purchase_timestamp"].dt.date.max()
    rfm_df["recency"] = rfm_df["max_order_timestamp"].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_order_timestamp", axis=1, inplace=True)
    return rfm_df

def create_top_product_categories_and_cities_df(df):
    category_sales = df.groupby('product_category_name_english').agg({'price': 'sum'}).reset_index()
    category_sales.rename(columns={"price": "total_sales"}, inplace=True)

    top_5_categories = category_sales.nlargest(5, 'total_sales')
    sales_by_city = df.groupby('geolocation_city').agg({'price': 'sum'}).reset_index()
    sales_by_city.rename(columns={"price": "total_sales"}, inplace=True)

    top_5_cities = sales_by_city.nlargest(5, 'total_sales')
    top_product_category = top_5_categories.iloc[0]['product_category_name_english']
    return top_5_categories, top_5_cities, top_product_category

def create_category_and_city_sales_df(df):
    category_sales_df = df.groupby('product_category_name').agg({'price': 'sum'}).reset_index()
    category_sales_df.rename(columns={"price": "total_sales"}, inplace=True)
    category_sales_df = category_sales_df.sort_values(by="total_sales", ascending=False).reset_index(drop=True)

    city_sales_df = df.groupby('geolocation_city').agg({'price': 'sum'}).reset_index()
    city_sales_df.rename(columns={"price": "total_sales"}, inplace=True)
    city_sales_df = city_sales_df.sort_values(by="total_sales", ascending=False).reset_index(drop=True)
    return category_sales_df, city_sales_df

# Load cleaned data
all_df = pd.read_csv("dashboard/all_data.csv")

# Mengonversi kolom tanggal menjadi tipe datetime
datetime_columns = ["order_purchase_timestamp", 
                    "shipping_limit_date", 
                    "order_delivered_customer_date", 
                    "order_approved_at", 
                    "order_delivered_carrier_date", 
                    "order_estimated_delivery_date"]

for column in datetime_columns:
    all_df[column] = pd.to_datetime(all_df[column])

all_df.sort_values(by="order_purchase_timestamp", inplace=True)
all_df.reset_index(drop=True, inplace=True)

min_date = all_df["order_purchase_timestamp"].min()
max_date = all_df["order_purchase_timestamp"].max()

# Sidebar untuk memilih rentang waktu
with st.sidebar:
    # Menambahkan logo perusahaan
    st.image("https://raw.githubusercontent.com/wndaazilla/img/2e0205f1ba72ed86509c1bafad3dc5485f717a32/ecommerce_public.png")
    
    start_date, end_date = st.date_input(
        label='Rentang Waktu', min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

main_df = all_df[(all_df["order_purchase_timestamp"] >= str(start_date)) & 
                  (all_df["order_purchase_timestamp"] <= str(end_date))]

# st.dataframe(main_df)

# Menyiapkan berbagai dataframe
daily_orders_df = create_daily_orders_df(main_df)
sum_order_items_df = create_sum_order_items_df(main_df)
rfm_df = create_rfm_df(main_df)
top_product_categories_and_cities_df = create_top_product_categories_and_cities_df(main_df)
category_and_city_sales_df = create_category_and_city_sales_df(main_df)

# Section for Daily Orders
st.header('E-Commerce Public Dashboard :bar_chart:')
st.subheader(':shopping_trolley: Daily Orders')

col1, col2 = st.columns(2)

with col1:
    total_orders = daily_orders_df.order_count.sum()
    st.metric("Total orders", value=total_orders)

with col2:
    total_revenue = format_currency(daily_orders_df.revenue.sum(), "AUD", locale='es_CO') 
    st.metric("Total Revenue", value=total_revenue)

fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
    daily_orders_df["order_purchase_timestamp"],
    daily_orders_df["order_count"],
    marker='o', 
    linewidth=2,
    color="#4092f3"
)
ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)
st.pyplot(fig)


# Section for RFM Value
st.subheader(":bust_in_silhouette: Best Customers Based on RFM Parameters")
rfm_df_sorted = rfm_df.sort_values(by='monetary', ascending=False)

col1, col2, col3 = st.columns(3)

with col1:
    avg_recency = round(rfm_df.recency.mean(), 1)
    st.metric("Average Recency (days)", value=avg_recency)

with col2:
    avg_frequency = round(rfm_df.frequency.mean(), 2)
    st.metric("Average Frequency", value=avg_frequency)

with col3:
    avg_frequency = format_currency(rfm_df.monetary.mean(), "AUD", locale='es_CO') 
    st.metric("Average Monetary", value=avg_frequency)

rfm_df_sorted['short_customer_id'] = rfm_df_sorted['customer_id'].apply(lambda x: x[:5])

fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(35, 10))
colors = ["#4092f3"] * 5

# Recency Plot
sns.barplot(y="recency", x="short_customer_id", 
            data=rfm_df_sorted.head(), 
            palette=colors, ax=ax[0], legend=False)
ax[0].set_ylabel(None)
ax[0].set_xlabel(None)
ax[0].set_title("Top Customers by Recency (days)", loc="center", fontsize=30)
ax[0].tick_params(axis='x', labelsize=25)
ax[0].tick_params(axis='y', labelsize=25)
ax[0].grid(False)

# Frequency Plot
sns.barplot(y="frequency", x="short_customer_id", 
            data=rfm_df_sorted.head(), 
            palette=colors, ax=ax[1], legend=False)
ax[1].set_ylabel(None)
ax[1].set_xlabel(None)
ax[1].set_title("Top Customers by Frequency", loc="center", fontsize=30)
ax[1].tick_params(axis='x', labelsize=25)
ax[1].tick_params(axis='y', labelsize=25)
ax[1].grid(False)

# Monetary Plot
sns.barplot(y="monetary", x="short_customer_id", 
            data=rfm_df_sorted.head(),  
            palette=colors, ax=ax[2], legend=False)
ax[2].set_ylabel(None)
ax[2].set_xlabel(None)
ax[2].set_title("Top Customers by Monetary Value", loc="center", fontsize=30)
ax[2].tick_params(axis='x', labelsize=25)
ax[2].tick_params(axis='y', labelsize=25)
ax[2].grid(False)
st.pyplot(fig)

# Section for Top Product Categories and Cities
st.subheader(":first_place_medal: Top Product Categories and Cities by Sales")

category_sales = main_df.groupby('product_category_name_english').agg({'price': 'sum'}).reset_index()
category_sales.rename(columns={"price": "total_sales"}, inplace=True)
top_5_categories = category_sales.nlargest(5, 'total_sales')

sales_by_city = main_df.groupby('geolocation_city').agg({'price': 'sum'}).reset_index()
sales_by_city.rename(columns={"price": "total_sales"}, inplace=True)
top_5_cities = sales_by_city.nlargest(5, 'total_sales')

top_product_category = top_5_categories.iloc[0]['product_category_name_english']

colors = ['#4092f3'] + ['#D3D3D3'] * 4
fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(35, 10))

sns.barplot(x='total_sales', y='product_category_name_english', data=top_5_categories,
            palette=colors, hue='product_category_name_english', legend=False, ax=ax[0])
ax[0].set_title('Top Product Categories by Total Sales', fontsize=45)
ax[0].set_xlabel(None)
ax[0].set_ylabel(None)
ax[0].tick_params(axis='x', labelsize=30)
ax[0].tick_params(axis='y', labelsize=30)
ax[0].grid(False)

sns.barplot(x='total_sales', y='geolocation_city', data=top_5_cities,
            palette=colors, hue='geolocation_city', legend=False, ax=ax[1])
ax[1].set_title(f'Top Cities for Product Category: \"{top_product_category}\"', fontsize=45)
ax[1].set_xlabel(None)
ax[1].set_ylabel(None)
ax[1].tick_params(axis='x', labelsize=28)
ax[1].tick_params(axis='y', labelsize=28)
ax[1].grid(False)
st.pyplot(fig)

# Section for Cities with the Highest Customers 
st.subheader(":classical_building: Top Cities with the Highest Customers")
top_cities = all_df.groupby('geolocation_city').agg(customer_count=('customer_id', 'nunique')).reset_index()
top_cities = top_cities.nlargest(10, 'customer_count')
top_cities = top_cities.sort_values('customer_count', ascending=True)

plt.figure(figsize=(6, 4))

colors = ['#D3D3D3'] * len(top_cities)
colors[-1] = '#4092f3'  

plt.barh(top_cities['geolocation_city'], top_cities['customer_count'], color=colors)

plt.title('Top Cities by Customer', fontsize=10)  
plt.xlabel(None)  
plt.ylabel(None) 

plt.tick_params(axis='x', labelsize=7)
plt.tick_params(axis='y', labelsize=7)
plt.tight_layout()  
st.pyplot(plt)

# Section for Highest Customers Area Map
st.subheader(':round_pushpin: Highest Customers Area Map')

top_cities = pd.DataFrame({
    'geolocation_city': ['sao paulo', 'rio de janeiro', 'belo horizonte', 'brasilia', 'curitiba', 
                         'campinas', 'porto alegre', 'salvador', 'guarulhos', 'sao bernardo do campo'],
    'geolocation_state': ['SP', 'RJ', 'MG', 'DF', 'PR', 'SP', 'RS', 'BA', 'SP', 'SP'],
    'geolocation_lat': [-23.5505, -22.9068, -19.9167, -15.7801, -25.4284, 
                        -22.9099, -30.0346, -12.9714, -23.4542, -23.691],
    'geolocation_lng': [-46.6333, -43.1729, -43.9345, -47.9292, -49.2733, 
                        -47.0626, -51.2177, -38.5014, -46.5333, -46.5646],
    'customer_count': [18290, 8004, 3214, 2238, 1792, 1714, 1625, 1476, 1366, 1102]
})

initial_location = [top_cities['geolocation_lat'].mean(), top_cities['geolocation_lng'].mean()]

# Membuat peta dengan folium
map_cities = folium.Map(location=initial_location, zoom_start=5)

marker_cluster = MarkerCluster().add_to(map_cities)

# Menambahkan marker untuk setiap pelanggan
for i, row in top_cities.iterrows():
    color = 'blue' if row['customer_count'] == top_cities['customer_count'].max() else 'gray'
    
    folium.Marker(
        location=[row['geolocation_lat'], row['geolocation_lng']],
        popup=f"{row['geolocation_city']}, {row['geolocation_state']}: {row['customer_count']} customers",
        icon=folium.Icon(color=color)
    ).add_to(marker_cluster)

folium_static(map_cities)
