//! Structural tests for the in-process `/report-tokens` trend chart.
//!
//! The retired matplotlib child left no recorded pixels to diff against, so
//! these pin what a consumer actually depends on: a well-framed truecolor PNG
//! of the documented size, a file name that cannot walk out of the plot
//! directory, and byte-for-byte determinism for one series.

use std::io::Read as _;

use flate2::read::ZlibDecoder;
use larch_core::report::cost_plot::render_cost_plot;

/// The eight-byte PNG signature every file opens with.
const SIGNATURE: [u8; 8] = [0x89, b'P', b'N', b'G', b'\r', b'\n', 0x1A, b'\n'];
/// Canvas width the renderer documents.
const WIDTH: u32 = 1000;
/// Canvas height the renderer documents.
const HEIGHT: u32 = 400;

fn points() -> Vec<(String, f64)> {
    vec![
        ("2026-05-01".to_owned(), 1.86),
        ("2026-05-02".to_owned(), 0.32),
        ("2026-05-03".to_owned(), 4.10),
    ]
}

/// Walk the chunk framing, returning each chunk's type and payload.
fn chunks(png: &[u8]) -> Vec<(String, Vec<u8>)> {
    assert_eq!(png[..8], SIGNATURE, "missing PNG signature");
    let mut offset = 8;
    let mut found = Vec::new();
    while offset < png.len() {
        let length = u32::from_be_bytes(png[offset..offset + 4].try_into().expect("length"));
        let length = usize::try_from(length).expect("chunk length fits in usize");
        let kind = String::from_utf8(png[offset + 4..offset + 8].to_vec()).expect("chunk type");
        let start = offset + 8;
        found.push((kind, png[start..start + length].to_vec()));
        // Length, type, payload, and the trailing four CRC bytes.
        offset = start + length + 4;
    }
    assert_eq!(offset, png.len(), "chunk framing overran the file");
    found
}

#[test]
fn renders_a_truecolor_png_of_the_documented_size() {
    let plot = render_cost_plot("design", "All runs", &points());
    let chunks = chunks(&plot.png);
    let kinds: Vec<&str> = chunks.iter().map(|(kind, _data)| kind.as_str()).collect();
    assert_eq!(kinds, ["IHDR", "IDAT", "IEND"]);
    let header = &chunks[0].1;
    assert_eq!(u32::from_be_bytes(header[0..4].try_into().unwrap()), WIDTH);
    assert_eq!(u32::from_be_bytes(header[4..8].try_into().unwrap()), HEIGHT);
    // Eight bits per sample, truecolor, deflate, adaptive filtering, no interlace.
    assert_eq!(header[8..13], [8, 2, 0, 0, 0]);
}

#[test]
fn the_image_data_inflates_to_filtered_rgb_scanlines() {
    let plot = render_cost_plot("implement", "All runs", &points());
    let chunks = chunks(&plot.png);
    let mut raw = Vec::new();
    ZlibDecoder::new(chunks[1].1.as_slice())
        .read_to_end(&mut raw)
        .expect("IDAT is a valid zlib stream");
    let stride = usize::try_from(WIDTH).unwrap() * 3 + 1;
    assert_eq!(raw.len(), stride * usize::try_from(HEIGHT).unwrap());
    assert!(
        raw.chunks(stride).all(|row| row[0] == 0),
        "every scanline uses filter type 0"
    );
    assert!(
        raw.chunks(stride)
            .any(|row| row[1..].iter().any(|&b| b != 0xFF)),
        "the chart painted something over the white canvas"
    );
}

#[test]
fn an_empty_series_still_renders_its_frame() {
    let empty = render_cost_plot("design", "All runs", &[]);
    assert_eq!(empty.file_name, "larch-report-tokens-all-runs.png");
    assert_eq!(empty.png[..8], SIGNATURE);
    assert_ne!(
        empty.png,
        render_cost_plot("design", "All runs", &points()).png,
        "an empty axes should not match a plotted series"
    );
}

#[test]
fn one_point_renders_without_a_division_by_zero() {
    let single = render_cost_plot("design", "All runs", &[("2026-05-01".to_owned(), 0.0)]);
    assert_eq!(chunks(&single.png).len(), 3);
}

#[test]
fn rendering_the_same_series_twice_is_byte_identical() {
    assert_eq!(
        render_cost_plot("design", "All runs", &points()).png,
        render_cost_plot("design", "All runs", &points()).png
    );
}

#[test]
fn a_label_cannot_walk_out_of_the_plot_directory() {
    for label in ["../../etc/passwd", "a/b", "a\\b", "All runs"] {
        let name = render_cost_plot("design", label, &[]).file_name;
        assert!(
            !name.contains('/') && !name.contains('\\'),
            "{label} produced a path-bearing file name: {name}"
        );
        assert!(name.starts_with("larch-report-tokens-"));
        assert_eq!(
            std::path::Path::new(&name)
                .extension()
                .and_then(|e| e.to_str()),
            Some("png")
        );
    }
}
