import streamlit as st
import networkx as nx
import osmnx as ox
import pandas as pd
import plotly.graph_objects as go
from functools import lru_cache

st.set_page_config(page_title="Best Emergency Station", page_icon="🚑", layout="wide")

st.title("🚑 Best Emergency Station")
st.caption("Proyek 08 Komputasi Graf • Lowokwaru, Kota Malang • NetworkX + Plotly + Streamlit")
st.markdown(
    "Aplikasi ini membandingkan calon pos darurat menggunakan jarak terpendek Dijkstra dan "
    "eksentrisitas pada subgraf jalan OpenStreetMap yang terdiri dari 20 simpul. "
    "Bobot adalah panjang jalan dalam meter, bukan waktu tempuh."
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
    distances = dict(nx.all_pairs_dijkstra_path_length(graph, weight="length"))
    paths = dict(nx.all_pairs_dijkstra_path(graph, weight="length"))
    n = graph.number_of_nodes()
    if not all(len(distances[node]) == n for node in graph.nodes()):
        raise ValueError("Validasi gagal: tidak semua simpul saling terjangkau.")
    eccentricity = {node: max(distances[node].values()) for node in graph.nodes()}
    radius = min(eccentricity.values())
    centers = [node for node, e in eccentricity.items() if abs(e - radius) < 1e-9]
    return distances, paths, eccentricity, radius, centers


def edge_options(graph, labels):
    options = []
    for u, v, data in graph.edges(data=True):
        text = f"{labels[u]} — {labels[v]} ({float(data['length']):.0f} m)"
        options.append((text, (u, v)))
    return sorted(options, key=lambda item: item[0])


def graph_figure(graph, labels, pos, candidate, farthest, centers, path, selected_edge=None, animate=False):
    # Draw the road network using node coordinates. Each simplified edge is shown as a segment.
    edge_x, edge_y = [], []
    for u, v in graph.edges():
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [pos[u][1], pos[v][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", name="Jalan / sisi graf",
        line=dict(color="#AAB2BD", width=1.5), hoverinfo="skip"
    ))
    node_list = list(graph.nodes())
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in node_list], y=[pos[n][1] for n in node_list],
        mode="markers+text", text=[labels[n] for n in node_list], textposition="top center",
        name="Persimpangan", marker=dict(size=9, color="#64748B"),
        customdata=[[labels[n], n] for n in node_list],
        hovertemplate="Simpul %{customdata[0]}<br>OSM ID: %{customdata[1]}<extra></extra>"
    ))
    if selected_edge is not None:
        u, v = selected_edge
        fig.add_trace(go.Scatter(x=[pos[u][0], pos[v][0]], y=[pos[u][1], pos[v][1]],
            mode="lines", name="Ruas yang diubah", line=dict(color="#A855F7", width=6), hoverinfo="skip"))

    route_x, route_y = [], []
    for u, v in zip(path[:-1], path[1:]):
        route_x += [pos[u][0], pos[v][0], None]
        route_y += [pos[u][1], pos[v][1], None]
    fig.add_trace(go.Scatter(x=route_x, y=route_y, mode="lines", name="Jalur terpendek ke titik terjauh",
        line=dict(color="#F59E0B", width=4), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in centers], y=[pos[n][1] for n in centers],
        mode="markers", name="Pusat graf", marker=dict(size=17, color="#16A34A", symbol="diamond", line=dict(color="white", width=1))))
    fig.add_trace(go.Scatter(x=[pos[candidate][0]], y=[pos[candidate][1]], mode="markers+text",
        text=["POS TERPILIH"], textposition="bottom center", name="Calon pos terpilih",
        marker=dict(size=20, color="#2563EB", symbol="square", line=dict(color="white", width=1))))
    fig.add_trace(go.Scatter(x=[pos[farthest][0]], y=[pos[farthest][1]], mode="markers+text",
        text=["TERJAUH"], textposition="top center", name="Titik terjauh",
        marker=dict(size=20, color="#DC2626", symbol="star", line=dict(color="white", width=1))))

    if animate and len(path) > 1:
        # Animate a marker along the shortest route. Plotly exposes Play/Pause controls.
        vehicle_index = len(fig.data)
        fig.add_trace(go.Scatter(x=[pos[path[0]][0]], y=[pos[path[0]][1]], mode="markers",
            name="Kendaraan (animasi)", marker=dict(size=15, color="#EA580C", symbol="circle")))
        frames = []
        for i, node in enumerate(path):
            frames.append(go.Frame(name=str(i), data=[go.Scatter(x=[pos[node][0]], y=[pos[node][1]])], traces=[vehicle_index]))
        fig.frames = frames
        fig.update_layout(updatemenus=[dict(type="buttons", showactive=False, x=0.02, y=1.13,
            buttons=[dict(label="▶ Putar", method="animate", args=[None, {"frame": {"duration": 650, "redraw": True}, "fromcurrent": True}]),
                     dict(label="⏸ Jeda", method="animate", args=[[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}])])])
    fig.update_layout(
        height=620, margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_title="Longitude", yaxis_title="Latitude",
        xaxis=dict(scaleanchor="y", scaleratio=1),
        title="Graf jalan Lowokwaru (subgraf 20 simpul)"
    )
    return fig

try:
    H, labels, pos, candidates = build_graph()
except Exception as exc:
    st.error("Jaringan OpenStreetMap belum berhasil diambil. Pastikan koneksi internet tersedia, lalu muat ulang aplikasi.")
    st.exception(exc)
    st.stop()

# Sidebar controls
st.sidebar.header("Kontrol aplikasi")
candidate_name = st.sidebar.selectbox("Pilih calon pos", list(candidates.keys()))
edge_items = edge_options(H, labels)
edge_labels = [item[0] for item in edge_items]
edge_lookup = {item[0]: item[1] for item in edge_items}
edge_label = st.sidebar.selectbox("Pilih ruas jalan untuk diubah", edge_labels)
factor = st.sidebar.slider("Faktor panjang ruas", min_value=1.0, max_value=3.0, value=1.0, step=0.25,
    help="1,00 = kondisi awal. Nilai lebih besar mensimulasikan ruas yang menjadi lebih panjang/terhambat.")
show_animation = st.sidebar.checkbox("Tampilkan animasi kendaraan", value=True)

selected_edge = edge_lookup[edge_label]
H_changed = H.copy()
u, v = selected_edge
original_length = float(H[u][v]["length"])
H_changed[u][v]["length"] = original_length * float(factor)

base_dist, base_paths, base_ecc, base_radius, base_centers = analyze(H)
changed_dist, changed_paths, changed_ecc, changed_radius, changed_centers = analyze(H_changed)
selected_node = candidates[candidate_name]
base_far = max(base_dist[selected_node], key=base_dist[selected_node].get)
changed_far = max(changed_dist[selected_node], key=changed_dist[selected_node].get)
base_path = base_paths[selected_node][base_far]
changed_path = changed_paths[selected_node][changed_far]

# Top metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Simpul dianalisis", H.number_of_nodes())
m2.metric("Sisi jalan", H.number_of_edges())
m3.metric("Eksentrisitas calon terpilih", f"{changed_ecc[selected_node]/1000:.3f} km", delta=f"{(changed_ecc[selected_node]-base_ecc[selected_node])/1000:+.3f} km dari awal")
m4.metric("Radius graf", f"{changed_radius/1000:.3f} km", delta=f"{(changed_radius-base_radius)/1000:+.3f} km dari awal")

st.subheader("1. Graf dan jalur menuju titik terjauh")
col_graph, col_info = st.columns([1.7, 1])
with col_graph:
    st.plotly_chart(graph_figure(H_changed, labels, pos, selected_node, changed_far, changed_centers,
        changed_path, selected_edge=selected_edge if factor != 1.0 else None, animate=show_animation), use_container_width=True)
with col_info:
    st.markdown("**Legenda**")
    st.markdown("- 🟦 Kotak biru: calon pos terpilih\n- 🟩 Berlian hijau: pusat graf\n- ⭐ Bintang merah: titik terjauh\n- 🟠 Garis oranye: jalur terpendek\n- 🟣 Garis ungu: ruas yang bobotnya dipilih untuk simulasi\n- 🟠 Titik bergerak: kendaraan pada animasi")
    st.markdown("**Rute terjauh saat ini**")
    st.write(" → ".join(labels[n] for n in changed_path))
    st.write(f"Jarak terjauh: **{changed_dist[selected_node][changed_far]:,.2f} m** ({changed_dist[selected_node][changed_far]/1000:.3f} km)")
    st.write(f"Jumlah simpul terjangkau: **{len(changed_dist[selected_node])}/{H_changed.number_of_nodes()}**")

st.subheader("2. Perbandingan kondisi awal dan setelah perubahan")
compare_rows = []
for name, node in candidates.items():
    base_far_node = max(base_dist[node], key=base_dist[node].get)
    new_far_node = max(changed_dist[node], key=changed_dist[node].get)
    compare_rows.append({
        "Calon pos": name,
        "Eksentrisitas awal (km)": base_ecc[node] / 1000,
        "Eksentrisitas setelah perubahan (km)": changed_ecc[node] / 1000,
        "Titik terjauh awal": labels[base_far_node],
        "Titik terjauh setelah perubahan": labels[new_far_node],
        "Simpul terjangkau": f"{len(changed_dist[node])}/{H_changed.number_of_nodes()}"
    })
compare_df = pd.DataFrame(compare_rows)
st.dataframe(compare_df.style.format({"Eksentrisitas awal (km)": "{:.3f}", "Eksentrisitas setelah perubahan (km)": "{:.3f}"}), use_container_width=True, hide_index=True)

winner = min(candidates, key=lambda name: changed_ecc[candidates[name]])
st.info(f"Berdasarkan eksentrisitas pada kondisi jaringan saat ini, calon dengan jarak terjauh terkecil adalah **{winner}**. Ini hanya rekomendasi berdasarkan jarak jaringan pada subgraf 20 simpul, bukan keputusan operasional akhir.")

st.subheader("3. Jarak terpendek dari calon pos terpilih ke semua simpul")
distance_rows = []
for node, distance in changed_dist[selected_node].items():
    distance_rows.append({"Simpul": labels[node], "OSM ID": node, "Jarak terpendek (m)": distance, "Jarak terpendek (km)": distance / 1000})
distance_df = pd.DataFrame(distance_rows).sort_values("Jarak terpendek (m)")
st.dataframe(distance_df.style.format({"Jarak terpendek (m)": "{:,.2f}", "Jarak terpendek (km)": "{:.3f}"}), use_container_width=True, hide_index=True)

with st.expander("Lihat eksentrisitas semua simpul dan pusat graf"):
    ecc_df = pd.DataFrame([{"Simpul": labels[n], "OSM ID": n, "Eksentrisitas (m)": changed_ecc[n], "Eksentrisitas (km)": changed_ecc[n]/1000, "Pusat graf": n in changed_centers} for n in H_changed.nodes()]).sort_values("Eksentrisitas (m)")
    st.dataframe(ecc_df.style.format({"Eksentrisitas (m)": "{:,.2f}", "Eksentrisitas (km)": "{:.3f}"}), use_container_width=True, hide_index=True)

st.subheader("4. Validasi dan interpretasi")
all_reachable = all(len(changed_dist[n]) == H_changed.number_of_nodes() for n in H_changed.nodes())
st.write(f"- Graf terhubung: **{'LULUS' if nx.is_connected(H_changed) else 'GAGAL'}**")
st.write(f"- Semua simpul terjangkau dengan Dijkstra: **{'LULUS' if all_reachable else 'GAGAL'}**")
st.write(f"- Bobot semua sisi nonnegatif: **{'LULUS' if all(float(d['length']) >= 0 for _, _, d in H_changed.edges(data=True)) else 'GAGAL'}**")
st.write(f"- Radius sama dengan eksentrisitas minimum: **{'LULUS' if abs(changed_radius-min(changed_ecc.values())) < 1e-9 else 'GAGAL'}**")
st.warning("Batas interpretasi: analisis hanya memakai 20 simpul pada subgraf terhubung; bobot adalah panjang jalan, bukan waktu tempuh. Model belum mempertimbangkan kepadatan penduduk, permintaan darurat, kapasitas layanan, kondisi lalu lintas, atau kelayakan lahan. Jaringan dibuat tak berarah sehingga jalan satu arah disederhanakan.")

st.caption("Catatan data: jaringan diambil dari OpenStreetMap saat aplikasi pertama kali dijalankan. Karena data OSM dapat berubah, subgraf dan hasil dapat sedikit berbeda dari hasil notebook yang dijalankan pada waktu lain.")
