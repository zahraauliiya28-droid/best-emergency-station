import streamlit as st
import networkx as nx
import osmnx as ox
import pandas as pd
import plotly.graph_objects as go
from functools import lru_cache
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Best Emergency Station",
    page_icon="🚑",
    layout="wide"
)


# =========================
# TEMA VISUAL DASHBOARD
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
    max-width: 1500px;
}

.stApp {
    background: linear-gradient(180deg, #EFF6FF 0%, #FFFFFF 55%);
}

.hero {
    background: linear-gradient(120deg, #0B1F33 0%, #123E63 58%, #087EAB 100%);
    padding: 2rem;
    border-radius: 22px;
    color: white;
    box-shadow: 0 12px 30px rgba(11, 31, 51, 0.18);
    margin: 0.5rem 0 1.4rem 0;
    border: 1px solid rgba(255,255,255,0.15);
}

.hero .eyebrow {
    color: #67E8F9 !important;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-size: 0.75rem !important;
    font-weight: 800;
    margin-bottom: 0.7rem;
}

.hero h1 {
    color: #FFFFFF;
    font-size: 2.35rem;
    font-weight: 800;
    margin: 0.2rem 0 0.7rem 0;
    line-height: 1.2;
}

.hero p {
    color: #DCEBFA;
    font-size: 0.98rem;
    margin: 0.35rem 0;
}

.hero .tagline {
    color: #A5F3FC;
    font-weight: 600;
}

.hero .author {
    border-top: 1px solid rgba(255,255,255,0.25);
    margin-top: 1.2rem;
    padding-top: 0.9rem;
    color: #E0F2FE;
    font-size: 0.9rem;
    font-weight: 600;
}

div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D8E7F5;
    border-radius: 16px;
    padding: 1rem 1.1rem;
    box-shadow: 0 5px 16px rgba(15, 42, 75, 0.06);
}

div[data-testid="stMetricLabel"] {
    color: #52677D;
    font-weight: 600;
}

div[data-testid="stMetricValue"] {
    color: #102A43;
    font-weight: 800;
}

section[data-testid="stSidebar"] {
    background: #F0F7FC;
    border-right: 1px solid #D5E5F2;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #102A43;
}

h2, h3 {
    color: #102A43;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #D8E7F5;
    border-radius: 14px;
    overflow: hidden;
}

div[data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #D8E7F5;
    border-radius: 16px;
    padding: 0.4rem;
    box-shadow: 0 5px 16px rgba(15, 42, 75, 0.04);
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

hr {
    border-color: #D8E7F5;
}
</style>

<div class="hero">
    <p class="eyebrow">PROYEK 08 DARURAT</p>
    <h1>🚑 Best Emergency Station</h1>
    <p>Bandingkan calon lokasi pos darurat melalui jarak terjauh ke titik layanan.</p>
    <p class="tagline">Eksentrisitas · Radius · Pusat Graf</p>
        Graph Optimization · Dijkstra · Eccentricity · Network Analysis
    </p>
    <p>📍 Lowokwaru, Kota Malang</p>
    <p class="author">
        Disusun oleh: Habibah Zahrotul Auliya · 240601110014
    </p>
</div>
""", unsafe_allow_html=True)


st.markdown("""
### 🎯 Tujuan Analisis

Aplikasi ini digunakan untuk membandingkan calon lokasi pos darurat
menggunakan algoritma **Dijkstra** dan konsep **eksentrisitas graf**.

- 🛣️ **Jarak terpendek:** menghitung jarak melalui jaringan jalan.
- 📍 **Eksentrisitas:** mengukur jarak maksimum dari suatu simpul ke simpul lain.
- 🎯 **Rekomendasi:** membandingkan calon pos berdasarkan jarak terjauh terkecil.

> **Catatan:** bobot sisi menyatakan panjang jalan dalam meter,
> bukan estimasi waktu tempuh kendaraan.
""")


@st.cache_resource
def build_graph():
    import pickle
    from pathlib import Path

    file_graf = Path(__file__).parent / "graf_emergency_station.pkl"

    with open(file_graf, "rb") as f:
        data = pickle.load(f)

    H = data["H"]
    labels = data["labels"]
    pos = data["pos"]
    candidate_nodes = data["candidates"]

    return H, labels, pos, candidate_nodes


def analyze(graph):
    distances = dict(
        nx.all_pairs_dijkstra_path_length(graph, weight="length")
    )
    paths = dict(
        nx.all_pairs_dijkstra_path(graph, weight="length")
    )

    n = graph.number_of_nodes()

    if not all(len(distances[node]) == n for node in graph.nodes()):
        raise ValueError(
            "Validasi gagal: tidak semua simpul saling terjangkau."
        )

    eccentricity = {
        node: max(distances[node].values())
        for node in graph.nodes()
    }

    radius = min(eccentricity.values())

    centers = [
        node for node, e in eccentricity.items()
        if abs(e - radius) < 1e-9
    ]

    return distances, paths, eccentricity, radius, centers


def edge_options(graph, labels):
    options = []

    for u, v, data in graph.edges(data=True):
        text = (
            f"{labels[u]} — {labels[v]} "
            f"({float(data['length']):.0f} m)"
        )
        options.append((text, (u, v)))

    return sorted(options, key=lambda item: item[0])

def road_map_figure(
    graph, labels, pos, candidate, farthest, centers,
    path, selected_edge=None
):
    # Pusat peta berdasarkan koordinat seluruh simpul
    latitudes = [pos[n][1] for n in graph.nodes()]
    longitudes = [pos[n][0] for n in graph.nodes()]

    center_lat = sum(latitudes) / len(latitudes)
    center_lon = sum(longitudes) / len(longitudes)

    # Peta dasar OpenStreetMap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles="OpenStreetMap"
    )

    # Jalur terpendek menuju titik terjauh
    route_coords = [
        [pos[n][1], pos[n][0]] for n in path
    ]

    folium.PolyLine(
        route_coords,
        color="#F59E0B",
        weight=6,
        opacity=0.9,
        tooltip="Jalur terpendek"
    ).add_to(m)

    # Semua simpul jaringan
    for node in graph.nodes():
        if node in (candidate, farthest) or node in centers:
            continue

        folium.CircleMarker(
            location=[pos[node][1], pos[node][0]],
            radius=4,
            color="#64748B",
            fill=True,
            fill_color="#94A3B8",
            fill_opacity=0.9,
            tooltip=f"Simpul: {labels[node]}"
        ).add_to(m)

    # Pusat graf
    for node in centers:
        folium.Marker(
            location=[pos[node][1], pos[node][0]],
            tooltip=f"Pusat graf: {labels[node]}",
            icon=folium.Icon(color="green", icon="star")
        ).add_to(m)

    # Calon pos terpilih
    folium.Marker(
        location=[pos[candidate][1], pos[candidate][0]],
        tooltip=f"Calon pos: {labels[candidate]}",
        icon=folium.Icon(color="blue", icon="plus-sign")
    ).add_to(m)

    # Titik terjauh
    folium.Marker(
        location=[pos[farthest][1], pos[farthest][0]],
        tooltip=f"Titik terjauh: {labels[farthest]}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)

    # Ruas jalan yang disimulasikan
    if selected_edge is not None:
        u, v = selected_edge
        folium.PolyLine(
            [
                [pos[u][1], pos[u][0]],
                [pos[v][1], pos[v][0]]
            ],
            color="#06B6D4",
            weight=7,
            opacity=1,
            tooltip="Ruas yang disimulasikan"
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

def graph_figure(
    graph, labels, pos, candidate, farthest, centers,
    path, selected_edge=None, animate=False
):
    edge_x, edge_y = [], []

    for u, v in graph.edges():
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [pos[u][1], pos[v][1], None]

    fig = go.Figure()

    # Jaringan jalan
    fig.add_trace(go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        name="Jalan / sisi graf",
        line=dict(color="#CBD5E1", width=2),
        hoverinfo="skip"
    ))

    # Simpul
    node_list = list(graph.nodes())

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in node_list],
        y=[pos[n][1] for n in node_list],
        mode="markers+text",
        text=[labels[n] for n in node_list],
        textposition="top center",
        textfont=dict(size=10, color="#1E293B"),
        name="Persimpangan",
        marker=dict(
            size=9,
            color="#64748B",
            line=dict(color="white", width=1.5)
        ),
        customdata=[[labels[n], n] for n in node_list],
        hovertemplate=(
            "<b>Simpul %{customdata[0]}</b>"
            "<br>OSM ID: %{customdata[1]}"
            "<extra></extra>"
        )
    ))

    # Ruas yang diubah dalam simulasi
    if selected_edge is not None:
        u, v = selected_edge

        fig.add_trace(go.Scatter(
            x=[pos[u][0], pos[v][0]],
            y=[pos[u][1], pos[v][1]],
            mode="lines",
            name="Ruas yang diubah",
           line=dict(color="#06B6D4", width=6),
            hoverinfo="skip"
        ))

    # Jalur terpendek menuju titik terjauh
    route_x, route_y = [], []

    for u, v in zip(path[:-1], path[1:]):
        route_x += [pos[u][0], pos[v][0], None]
        route_y += [pos[u][1], pos[v][1], None]

    fig.add_trace(go.Scatter(
        x=route_x,
        y=route_y,
        mode="lines",
        name="Jalur terpendek",
        line=dict(color="#F59E0B", width=4.5),
        hoverinfo="skip"
    ))

    # Pusat graf
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in centers],
        y=[pos[n][1] for n in centers],
        mode="markers",
        name="Pusat graf",
        marker=dict(
            size=18,
            color="#16A34A",
            symbol="diamond",
            line=dict(color="white", width=2)
        ),
        hovertemplate="Pusat graf<extra></extra>"
    ))

    # Calon pos terpilih
    fig.add_trace(go.Scatter(
        x=[pos[candidate][0]],
        y=[pos[candidate][1]],
        mode="markers+text",
        text=["POS TERPILIH"],
        textposition="bottom center",
        textfont=dict(size=11, color="#1D4ED8"),
        name="Calon pos terpilih",
        marker=dict(
            size=20,
            color="#2563EB",
            symbol="square",
            line=dict(color="white", width=2)
        ),
        hovertemplate="Calon pos terpilih<extra></extra>"
    ))

    # Titik terjauh
    fig.add_trace(go.Scatter(
        x=[pos[farthest][0]],
        y=[pos[farthest][1]],
        mode="markers+text",
        text=["TERJAUH"],
        textposition="top center",
        textfont=dict(size=11, color="#B91C1C"),
        name="Titik terjauh",
        marker=dict(
            size=20,
            color="#DC2626",
            symbol="star",
            line=dict(color="white", width=2)
        ),
        hovertemplate="Titik terjauh<extra></extra>"
    ))

    # Animasi kendaraan pada jalur
    if animate and len(path) > 1:
        vehicle_index = len(fig.data)

        fig.add_trace(go.Scatter(
            x=[pos[path[0]][0]],
                        y=[pos[path[0]][1]],
            mode="markers",
            name="Kendaraan",
            marker=dict(
                size=15,
                color="#EA580C",
                symbol="circle",
                line=dict(color="white", width=2)
            )
        ))

        frames = []

        for i, node in enumerate(path):
            frames.append(go.Frame(
                name=str(i),
                data=[go.Scatter(
                    x=[pos[node][0]],
                    y=[pos[node][1]]
                )],
                traces=[vehicle_index]
            ))

        fig.frames = frames

        fig.update_layout(
            updatemenus=[dict(
                type="buttons",
                direction="right",
                showactive=False,
                x=0.02,
                xanchor="left",
                y=1.08,
                yanchor="top",
                bgcolor="white",
                bordercolor="#CBD5E1",
                borderwidth=1,
                font=dict(color="#10243A", size=11),
                buttons=[
                    dict(
                        label="▶ Putar",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {
                                    "duration": 650,
                                    "redraw": True
                                },
                                "fromcurrent": True,
                                "transition": {
                                    "duration": 250,
                                    "easing": "cubic-in-out"
                                }
                            }
                        ]
                    ),
                    dict(
                        label="⏸ Jeda",
                        method="animate",
                        args=[
                            [None],
                            {
                                "mode": "immediate",
                                "frame": {
                                    "duration": 0,
                                    "redraw": False
                                },
                                "transition": {"duration": 0}
                            }
                        ]
                    )
                ]
            )]
        )

    
    # Tata letak graf
    fig.update_layout(
        height=590,
        margin=dict(l=35, r=25, t=70, b=40),
        showlegend=True,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F7FBFF",
        font=dict(
            family="Arial, sans-serif",
            color="#334155",
            size=11
        ),
        xaxis=dict(
            title="Longitude",
            showgrid=True,
            gridcolor="#E2EAF2",
            zeroline=False,
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            title="Latitude",
            showgrid=True,
            gridcolor="#E2EAF2",
            zeroline=False
        ),
        hoverlabel=dict(
            bgcolor="#102A43",
            font_color="#FFFFFF"
        )
    )

    return fig

# Memuat data graf
try:
    H, labels, pos, candidates = build_graph()
except Exception as exc:
    st.error(
        "Graf gagal dimuat. Pastikan file "
        "`graf_emergency_station.pkl` tersedia di repositori."
    )
    st.exception(exc)
    st.stop()

# =========================

# =========================
# SIDEBAR: KONTROL APLIKASI
# =========================
st.sidebar.markdown("## 🚑 Pusat Kontrol")
st.sidebar.caption("Atur parameter untuk menguji jaringan jalan.")

st.sidebar.markdown("### 📍 Lokasi Pos")

candidate_name = st.sidebar.selectbox(
    "Pilih calon pos darurat",
    list(candidates.keys())
)

st.sidebar.divider()
st.sidebar.markdown("### 🛣️ Simulasi Jalan")

edge_items = edge_options(H, labels)
edge_labels = [item[0] for item in edge_items]
edge_lookup = {item[0]: item[1] for item in edge_items}

edge_label = st.sidebar.selectbox(
    "Pilih ruas jalan",
    edge_labels
)

factor = st.sidebar.slider(
    "Faktor perubahan panjang",
    min_value=1.0,
    max_value=3.0,
    value=1.0,
    step=0.25,
    help=(
        "1,00 berarti kondisi awal. "
        "Faktor lebih besar menyimulasikan ruas jalan yang lebih panjang."
    )
)

show_animation = st.sidebar.checkbox(
    "🚑 Aktifkan animasi kendaraan",
    value=True
)

st.sidebar.divider()
st.sidebar.markdown("### 🎨 Legenda Graf")

st.sidebar.markdown("""
🟦 **Biru** — calon pos terpilih

🟩 **Hijau** — pusat graf

⭐ **Merah** — titik terjauh

🟠 **Oranye** — jalur terpendek

🟣 **Ungu** — ruas yang disimulasikan

🚑 **Oranye bergerak** — kendaraan
""")

st.sidebar.info(
    "Ubah calon pos atau faktor ruas untuk melihat "
    "bagaimana hasil analisis jaringan berubah."
)


# =========================
# ANALISIS JARINGAN
# =========================
selected_edge = edge_lookup[edge_label]

H_changed = H.copy()
u, v = selected_edge

original_length = float(H[u][v]["length"])
H_changed[u][v]["length"] = original_length * float(factor)
simulated_length = float(H_changed[u][v]["length"])

base_dist, base_paths, base_ecc, base_radius, base_centers = analyze(H)
changed_dist, changed_paths, changed_ecc, changed_radius, changed_centers = analyze(
    H_changed
)

selected_node = candidates[candidate_name]

base_far = max(
    base_dist[selected_node],
    key=base_dist[selected_node].get
)

changed_far = max(
    changed_dist[selected_node],
    key=changed_dist[selected_node].get
)

changed_path = changed_paths[selected_node][changed_far]



# =========================
# METRIK UTAMA
# =========================
st.subheader("📊 Ringkasan Jaringan")

ecc_delta = (
    changed_ecc[selected_node] - base_ecc[selected_node]
) / 1000

radius_delta = (changed_radius - base_radius) / 1000

ecc_delta_text = (
    f"{ecc_delta:+.3f} km dari kondisi awal"
    if abs(ecc_delta) > 1e-9
    else "Tidak berubah dari kondisi awal"
)

radius_delta_text = (
    f"{radius_delta:+.3f} km dari kondisi awal"
    if abs(radius_delta) > 1e-9
    else "Tidak berubah dari kondisi awal"
)

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "🔵 Jumlah Simpul",
    H.number_of_nodes()
)

m2.metric(
    "🛣️ Jumlah Sisi Jalan",
    H.number_of_edges()
)

m3.metric(
    "📏 Eksentrisitas Pos",
    f"{changed_ecc[selected_node] / 1000:.3f} km",
    delta=ecc_delta_text,
    delta_color="off"
)

m4.metric(
    "🎯 Radius Graf",
    f"{changed_radius / 1000:.3f} km",
    delta=radius_delta_text,
    delta_color="off"
)

st.markdown("#### 🧪 Ringkasan Simulasi Ruas Jalan")

simulated_length = float(H_changed[u][v]["length"])

s1, s2, s3 = st.columns(3)

s1.metric(
    "Panjang Awal",
    f"{original_length:,.2f} m"
)

s2.metric(
    "Faktor Simulasi",
    f"{factor:.2f}×"
)

s3.metric(
    "Panjang Simulasi",
    f"{simulated_length:,.2f} m",
    delta=f"{simulated_length - original_length:+,.2f} m",
    delta_color="off"
)

st.caption(
    f"Ruas yang diuji: {labels[u]} — {labels[v]}. "
    "Perubahan ini merupakan simulasi bobot matematis, "
    "bukan perubahan kondisi jalan nyata."
)

# =========================
# GRAF DAN RUTE
# =========================
st.divider()
st.subheader("1. Visualisasi jaringan dan jalur terjauh")

col_graph, col_info = st.columns([2.1, 1])


with col_graph:
    map_fig = road_map_figure(
        H_changed,
        labels,
        pos,
        selected_node,
        changed_far,
        changed_centers,
        changed_path,
        selected_edge=selected_edge if factor != 1.0 else None
    )

    st_folium(
        map_fig,
        use_container_width=True,
        height=590,
        key="best_emergency_station_map"
    )


with col_info:
    st.markdown("#### Keterangan graf")

    st.markdown(
    "🟦 **Kotak biru** — calon pos terpilih  \n"
    "🟩 **Berlian hijau** — pusat graf  \n"
    "⭐ **Bintang merah** — titik terjauh  \n"
    "🟠 **Garis oranye** — jalur terpendek  \n"
    "🟣 **Garis ungu** — ruas yang diubah  \n"
    "🚑 **Titik bergerak** — animasi kendaraan"
)

    st.divider()
    st.markdown("#### Informasi rute")

    st.write(f"**Calon pos:** {candidate_name}")
    st.write(f"**Titik terjauh:** {labels[changed_far]}")

    rute_meter = changed_dist[selected_node][changed_far]

    st.metric(
        "Jarak terjauh",
        f"{rute_meter / 1000:.3f} km"
    )

    st.caption(
        f"{rute_meter:,.2f} meter · "
        f"{len(changed_dist[selected_node])}/"
        f"{H_changed.number_of_nodes()} simpul terjangkau"
    )

# =========================
# PERBANDINGAN CALON POS
# =========================
st.divider()
st.subheader("2. Perbandingan kondisi awal dan simulasi")
st.caption(
    "Kondisi awal memakai bobot jalan asli pada subgraf. "
    "Kondisi simulasi memakai bobot ruas terpilih setelah dikalikan faktor."
)

compare_rows = []

for name, node in candidates.items():
    base_far_node = max(
        base_dist[node],
        key=base_dist[node].get
    )

    new_far_node = max(
        changed_dist[node],
        key=changed_dist[node].get
    )

    compare_rows.append({
        "Calon pos": name,
        "Eksentrisitas awal (km)": base_ecc[node] / 1000,
        "Eksentrisitas simulasi (km)": changed_ecc[node] / 1000,
        "Titik terjauh awal": labels[base_far_node],
        "Titik terjauh simulasi": labels[new_far_node],
        "Simpul terjangkau": (
            f"{len(changed_dist[node])}/{H_changed.number_of_nodes()}"
        )
    })

compare_df = pd.DataFrame(compare_rows)

st.dataframe(
    compare_df.style.format({
        "Eksentrisitas awal (km)": "{:.3f}",
        "Eksentrisitas simulasi (km)": "{:.3f}"
    }),
    use_container_width=True,
    hide_index=True
)

winner = min(
    candidates,
    key=lambda name: changed_ecc[candidates[name]]
)

st.success(
    f"**Rekomendasi berdasarkan eksentrisitas: {winner}.** "
    "Calon ini memiliki jarak terjauh yang paling kecil "
    "di antara calon yang dibandingkan pada jaringan saat ini."
)

st.info(
    "Rekomendasi ini berdasarkan panjang jalan pada subgraf "
    "20 simpul, bukan keputusan operasional akhir."
)


# =========================
# TABEL JARAK TERPENDEK
# =========================
st.divider()
st.subheader("3. Jarak terpendek ke semua simpul")

distance_rows = []

for node, distance in changed_dist[selected_node].items():
    distance_rows.append({
        "Simpul": labels[node],
        "OSM ID": node,
        "Jarak terpendek (m)": distance,
        "Jarak terpendek (km)": distance / 1000
    })

distance_df = pd.DataFrame(distance_rows).sort_values(
    "Jarak terpendek (m)"
)

st.dataframe(
    distance_df.style.format({
        "Jarak terpendek (m)": "{:,.2f}",
        "Jarak terpendek (km)": "{:.3f}"
    }),
    use_container_width=True,
    hide_index=True
)


# =========================
# EKSENTRISITAS SEMUA SIMPUL
# =========================
with st.expander("Lihat eksentrisitas semua simpul dan pusat graf"):
    ecc_df = pd.DataFrame([
        {
            "Simpul": labels[n],
            "OSM ID": n,
            "Eksentrisitas (m)": changed_ecc[n],
            "Eksentrisitas (km)": changed_ecc[n] / 1000,
            "Pusat graf": n in changed_centers
        }
        for n in H_changed.nodes()
    ]).sort_values("Eksentrisitas (m)")

    st.dataframe(
        ecc_df.style.format({
            "Eksentrisitas (m)": "{:,.2f}",
            "Eksentrisitas (km)": "{:.3f}"
        }),
        use_container_width=True,
        hide_index=True
    )


# =========================
# VALIDASI DAN KETERBATASAN
# =========================
st.divider()
st.subheader("4. Validasi dan interpretasi")

all_reachable = all(
    len(changed_dist[n]) == H_changed.number_of_nodes()
    for n in H_changed.nodes()
)

checks = [
    (
        "Graf terhubung",
        nx.is_connected(H_changed)
    ),
    (
        "Semua simpul terjangkau dengan Dijkstra",
        all_reachable
    ),
    (
        "Bobot semua sisi nonnegatif",
        all(
            float(data["length"]) >= 0
            for _, _, data in H_changed.edges(data=True)
        )
    ),
    (
        "Radius sama dengan eksentrisitas minimum",
        abs(
            changed_radius - min(changed_ecc.values())
        ) < 1e-9
    )
]

for description, passed in checks:
    if passed:
        st.success(f"✓ {description}: LULUS")
    else:
        st.error(f"✗ {description}: GAGAL")

st.warning(
    "**Keterbatasan model:** analisis hanya menggunakan 20 simpul "
    "pada subgraf terhubung. Bobot menyatakan panjang jalan, bukan "
    "waktu tempuh. Model belum mempertimbangkan kepadatan penduduk, "
    "permintaan darurat, kapasitas layanan, kondisi lalu lintas, "
    "atau kelayakan lahan. Jaringan tak berarah juga menyederhanakan "
    "kondisi jalan satu arah."
)

# =========================
# PERTANYAAN PRESENTASI
# =========================
st.divider()
st.subheader("5. Pertanyaan Presentasi")

st.markdown("""
**Mengapa pos yang tampak berada di tengah gambar belum tentu menjadi pusat graf?**

Posisi tengah pada gambar hanya menunjukkan letak geometris.
Sementara itu, pusat graf ditentukan berdasarkan eksentrisitas,
yaitu jarak terpendek maksimum dari suatu simpul ke seluruh simpul lain.
Karena panjang dan susunan jalan berbeda-beda, simpul yang berada
di tengah gambar belum tentu memiliki eksentrisitas minimum.
""")

st.caption(
    "Best Emergency Station · Proyek 08 Komputasi Graf · "
    "Lowokwaru, Kota Malang"
)
