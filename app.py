        vehicle_index = len(fig.data)
        fig.add_trace(go.Scatter(x=[pos[path[0]][0]], y=[pos[path[0]][1]], mode="markers",
            name="Kendaraan (animasi)", marker=dict(size=15, color="#EA580C", symbol="circle")))
        frames = []
        for i, node in enumerate(path):
            frames.append(go.Frame(name=str(i), data=[go.Scatter(x=[pos[node][0]], y=[pos[node][1]])], traces=[vehicle_index]))
        fig.frames = frames
        fig.update_layout(updatemenus=[dict(type="buttons", showactive=False, x=0.02, y=1.08,
            buttons=[dict(label="▶ Putar", method="animate", args=[None, {"frame": {"duration": 650, "redraw": True}, "fromcurrent": True}]),
                     dict(label="⏸ Jeda", method="animate", args=[[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}])])])
    
    fig.update_layout(
        height=680,
        margin=dict(l=30, r=20, t=100, b=55),
        showlegend=False,
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        xaxis=dict(scaleanchor="y", scaleratio=1),
        title=None
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
col_graph, col_info = st.columns([2.05, 1])
with col_graph:
    st.plotly_chart(graph_figure(H_changed, labels, pos, selected_node, changed_far, changed_centers,
        changed_path, selected_edge=selected_edge if factor != 1.0 else None, animate=show_animation), width="stretch")
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
