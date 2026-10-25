import streamlit as st
import networkx as nx
import osmnx as ox
import pandas as pd
import plotly.graph_objects as go
from functools import lru_cache

st.set_page_config(
    page_title="Best Emergency Station",
    page_icon="🚑",
    layout="wide"
)

# Tema visual dashboard
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
    max-width: 1500px;
}
.stApp {
    background: linear-gradient(180deg, #F4F8FC 0%, #FFFFFF 42%);
}
.hero {
    background: linear-gradient(120deg, #10243A 0%, #173F67 62%, #2563EB 100%);
    padding: 1.55rem 1.8rem;
    border-radius: 20px;
    color: white;
    box-shadow: 0 12px 28px rgba(16,36,58,.16);
    margin-bottom: 1rem;
}
.hero h1 {
    color: white;
    font-size: 2.05rem;
    margin: 0 0 .35rem 0;
}
.hero p {
    color: #DCEBFA;
    margin: .2rem 0;
    font-size: .98rem;
}
.eyebrow {
    text-transform: uppercase;
    letter-spacing: .14em;
    font-size: .72rem !important;
    font-weight: 700;
    color: #93C5FD !important;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 15px;
    padding: 1rem 1.05rem;
    box-shadow: 0 4px 14px rgba(15,23,42,.045);
}
div[data-testid="stMetricLabel"] {
    color: #64748B;
}
div[data-testid="stMetricValue"] {
    color: #10243A;
}
section[data-testid="stSidebar"] {
    background: #F0F5FA;
    border-right: 1px solid #DCE5EF;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #10243A;
}
h2, h3 {
    color: #10243A;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    overflow: hidden;
}
hr {
    border-color: #E2E8F0;
}
</style>

<div class="hero">
  <p class="eyebrow">PROYEK 08 · KOMPUTASI GRAF</p>
  <h1>🚑 Best Emergency Station</h1>
  <p>Analisis lokasi pos darurat · Lowokwaru, Kota Malang</p>
  <p>NetworkX · Dijkstra · Eccentricity · Streamlit</p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "Aplikasi ini membandingkan calon pos darurat berdasarkan "
    "**jarak terpendek Dijkstra** dan **eksentrisitas** pada subgraf "
    "jalan yang terdiri dari 20 simpul. Bobot sisi menyatakan panjang "
    "jalan (meter), bukan waktu tempuh."
)


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
        textfont=dict(size=10, color="#334155"),
        name="Persimpangan",
        marker=dict(
            size=10,
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
            line=dict(color="#A855F7", width=6),
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
        height=650,
        margin=dict(l=35, r=25, t=90, b=55),
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="#F8FAFC",
        font=dict(
            family="Arial, sans-serif",
            color="#334155",
            size=11
        ),
        xaxis=dict(
            title="Longitude",
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=False,
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            title="Latitude",
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=False
        ),
        hoverlabel=dict(
            bgcolor="#10243A",
            font_color="white"
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
# SIDEBAR: KONTROL APLIKASI
# =========================
st.sidebar.title("🚑 Kontrol Dashboard")
st.sidebar.caption("Atur simulasi jaringan jalan.")

candidate_name = st.sidebar.selectbox(
    "Pilih calon pos darurat",
    list(candidates.keys())
)

edge_items = edge_options(H, labels)
edge_labels = [item[0] for item in edge_items]
edge_lookup = {item[0]: item[1] for item in edge_items}

edge_label = st.sidebar.selectbox(
    "Pilih ruas jalan untuk diubah",
    edge_labels
)

factor = st.sidebar.slider(
    "Faktor panjang ruas",
    min_value=1.0,
    max_value=3.0,
    value=1.0,
    step=0.25,
    help=(
        "1,00 = kondisi awal. Nilai lebih besar "
        "mensimulasikan ruas yang menjadi lebih panjang."
    )
)

show_animation = st.sidebar.checkbox(
    "Tampilkan animasi kendaraan",
    value=True
)

st.sidebar.divider()
st.sidebar.markdown("**Panduan warna graf**")
st.sidebar.markdown(
    "🟦 Calon pos terpilih  \n"
    "🟩 Pusat graf  \n"
    "⭐ Titik terjauh  \n"
    "🟠 Jalur terpendek  \n"
    "🟣 Ruas yang diubah  \n"
    "🟠 Kendaraan animasi"
)


# =========================
# ANALISIS JARINGAN
# =========================
selected_edge = edge_lookup[edge_label]

H_changed = H.copy()
u, v = selected_edge

original_length = float(H[u][v]["length"])
H_changed[u][v]["length"] = original_length * float(factor)

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
st.subheader("Ringkasan jaringan")

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Jumlah simpul",
    H.number_of_nodes()
)

m2.metric(
    "Jumlah sisi jalan",
    H.number_of_edges()
)

m3.metric(
    "Eksentrisitas calon pos",
    f"{changed_ecc[selected_node] / 1000:.3f} km",
    delta=(
        f"{(changed_ecc[selected_node] - base_ecc[selected_node]) / 1000:+.3f} km"
        " dari kondisi awal"
    )
)

m4.metric(
    "Radius graf",
    f"{changed_radius / 1000:.3f} km",
    delta=(
        f"{(changed_radius - base_radius) / 1000:+.3f} km"
        " dari kondisi awal"
    )
)


# =========================
# GRAF DAN RUTE
# =========================
st.divider()
st.subheader("1. Visualisasi jaringan dan jalur terjauh")

col_graph, col_info = st.columns([2.1, 1])

with col_graph:
    fig = graph_figure(
        H_changed,
        labels,
        pos,
        selected_node,
        changed_far,
        changed_centers,
        changed_path,
        selected_edge=selected_edge if factor != 1.0 else None,
        animate=show_animation
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "responsive": True
        }
    )

with col_info:
    st.markdown("#### Keterangan graf")

    st.markdown(
        "🟦 **Kotak biru** — calon pos terpilih  \n"
        "🟩 **Berlian hijau** — pusat graf  \n"
        "⭐ **Bintang merah** — titik terjauh  \n"
        "🟠 **Garis oranye** — jalur terpendek  \n"
        "🟣 **Garis ungu** — ruas yang diubah  \n"
        "🟠 **Titik bergerak** — animasi kendaraan"
    )

    st.divider()
    st.markdown("#### Informasi rute")

    st.write(
        f"**Calon pos:** {candidate_name}"
    )

    st.write(
        f"**Titik terjauh:** {labels[changed_far]}"
    )

    st.write(
        f"**Jarak terjauh:** "
        f"{changed_dist[selected_node][changed_far]:,.2f} m"
    )

    st.write(
        f"**Jarak dalam km:** "
        f"{changed_dist[selected_node][changed_far] / 1000:.3f} km"
    )

    st.write(
        f"**Jumlah simpul terjangkau:** "
        f"{len(changed_dist[selected_node])}/{H_changed.number_of_nodes()}"
    )

    st.caption(
        "Panjang rute dihitung menggunakan algoritma Dijkstra "
        "dengan bobot panjang jalan."
    )


# =========================
# PERBANDINGAN CALON POS
# =========================
st.divider()
st.subheader("2. Perbandingan kondisi awal dan simulasi")

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

st.caption(
    "Best Emergency Station · Proyek 08 Komputasi Graf · "
    "Lowokwaru, Kota Malang"
)       
