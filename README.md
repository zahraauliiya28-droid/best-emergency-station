# Best Emergency Station — Proyek 08 Komputasi Graf

Aplikasi Streamlit untuk membandingkan dua calon lokasi pos darurat di Lowokwaru, Malang, menggunakan subgraf jalan OpenStreetMap berisi 20 simpul, Dijkstra, eksentrisitas, radius, dan pusat graf.

## Menjalankan di komputer

1. Pastikan Python 3.10 atau lebih baru terpasang.
2. Ekstrak folder proyek ini.
3. Buka Terminal / Command Prompt pada folder proyek.
4. Pasang dependensi:

   ```bash
   pip install -r requirements.txt
   ```

5. Jalankan aplikasi:

   ```bash
   streamlit run app.py
   ```

6. Browser akan membuka alamat lokal Streamlit (biasanya `http://localhost:8501`).

## Fitur

- Memilih Calon Pos A atau B.
- Melihat jarak terpendek ke seluruh simpul.
- Mengubah faktor panjang satu ruas jalan (1.00–3.00).
- Membandingkan eksentrisitas sebelum dan sesudah perubahan.
- Menampilkan titik terjauh, jalur terpendek, radius, dan pusat graf.
- Visualisasi Plotly dengan kontrol animasi Play/Pause.
- Validasi keterjangkauan dan bobot sisi.

## Catatan penting

- Aplikasi memerlukan koneksi internet saat mengambil jaringan dari OpenStreetMap.
- Data diambil ketika aplikasi pertama kali dijalankan; hasil dapat berubah jika data OpenStreetMap berubah.
- Subgraf analisis berisi 20 simpul, bukan seluruh jaringan Lowokwaru.
- Bobot adalah panjang jalan dalam meter, bukan estimasi waktu tempuh.
- Graf dimodelkan tak berarah; jalan satu arah disederhanakan.
- Hasil hanya rekomendasi berdasarkan jarak jaringan, bukan keputusan operasional yang mempertimbangkan populasi, permintaan, kapasitas, lalu lintas, dan kelayakan lahan.
