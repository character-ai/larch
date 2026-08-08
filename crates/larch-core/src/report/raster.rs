//! Minimal RGB canvas and PNG encoder for larch's generated charts.
//!
//! `/report-tokens` used to hand its trend series to a matplotlib child. The
//! chart is a line, a few grid rules, and short ASCII labels, so the pixels are
//! produced here instead of spawning an interpreter: a canvas with line, disc,
//! and bitmap-text primitives, and a PNG writer over the workspace `flate2`
//! dependency. Nothing here is chart-aware; [`super::cost_plot`] owns the
//! layout.

use std::io::Write as _;

use flate2::{Compression, write::ZlibEncoder};

/// One opaque RGB color.
pub type Color = [u8; 3];

/// Pixel rows in one glyph, as the glyph array length.
const GLYPH_HEIGHT: usize = 7;
/// Pixel rows in one glyph, as pixel arithmetic uses it.
const GLYPH_ROWS: i32 = 7;
/// Pixel columns in one glyph, before the one-pixel advance gap.
const GLYPH_WIDTH: i32 = 5;
/// Columns one character advances, including the gap to the next glyph.
const ADVANCE: i32 = GLYPH_WIDTH + 1;
/// Bytes per pixel in the canvas buffer and the encoded PNG.
const CHANNELS: usize = 3;

/// One glyph: seven rows of five pixels, most significant bit leftmost.
type Glyph = [u8; GLYPH_HEIGHT];

/// Blank glyph, used for the space and for any unsupported character.
const BLANK: Glyph = [0; GLYPH_HEIGHT];

/// `0` through `9`.
#[rustfmt::skip]
const DIGITS: [Glyph; 10] = [
    [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
];

/// `A` through `Z`.
#[rustfmt::skip]
const UPPERCASE: [Glyph; 26] = [
    [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    [0b11100, 0b10010, 0b10001, 0b10001, 0b10001, 0b10010, 0b11100],
    [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111],
    [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
    [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
];

/// `a` through `z`.
#[rustfmt::skip]
const LOWERCASE: [Glyph; 26] = [
    [0b00000, 0b00000, 0b01110, 0b00001, 0b01111, 0b10001, 0b01111],
    [0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b11110],
    [0b00000, 0b00000, 0b01110, 0b10001, 0b10000, 0b10001, 0b01110],
    [0b00001, 0b00001, 0b01111, 0b10001, 0b10001, 0b10001, 0b01111],
    [0b00000, 0b00000, 0b01110, 0b10001, 0b11111, 0b10000, 0b01110],
    [0b00110, 0b01001, 0b01000, 0b11100, 0b01000, 0b01000, 0b01000],
    [0b00000, 0b00000, 0b01111, 0b10001, 0b01111, 0b00001, 0b01110],
    [0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001],
    [0b00100, 0b00000, 0b01100, 0b00100, 0b00100, 0b00100, 0b01110],
    [0b00010, 0b00000, 0b00110, 0b00010, 0b00010, 0b10010, 0b01100],
    [0b10000, 0b10000, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010],
    [0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    [0b00000, 0b00000, 0b11010, 0b10101, 0b10101, 0b10101, 0b10101],
    [0b00000, 0b00000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001],
    [0b00000, 0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
    [0b00000, 0b00000, 0b11110, 0b10001, 0b11110, 0b10000, 0b10000],
    [0b00000, 0b00000, 0b01111, 0b10001, 0b01111, 0b00001, 0b00001],
    [0b00000, 0b00000, 0b10110, 0b11001, 0b10000, 0b10000, 0b10000],
    [0b00000, 0b00000, 0b01111, 0b10000, 0b01110, 0b00001, 0b11110],
    [0b01000, 0b01000, 0b11100, 0b01000, 0b01000, 0b01001, 0b00110],
    [0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b10011, 0b01101],
    [0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    [0b00000, 0b00000, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010],
    [0b00000, 0b00000, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001],
    [0b00000, 0b00000, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110],
    [0b00000, 0b00000, 0b11111, 0b00010, 0b00100, 0b01000, 0b11111],
];

/// The glyph for one character, blank when the font does not cover it.
///
/// The font covers exactly what larch's chart labels contain: ASCII letters,
/// digits, and the four separators a series label, a tick value, or an ISO date
/// can carry.
#[rustfmt::skip]
const fn glyph(character: char) -> Glyph {
    match character {
        '0'..='9' => DIGITS[character as usize - '0' as usize],
        'A'..='Z' => UPPERCASE[character as usize - 'A' as usize],
        'a'..='z' => LOWERCASE[character as usize - 'a' as usize],
        '-' => [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
        '.' => [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100],
        ':' => [0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000],
        '_' => [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b11111],
        _unsupported => BLANK,
    }
}

/// Width in pixels of one string drawn at `scale`, without the trailing gap.
pub fn text_width(text: &str, scale: i32) -> i32 {
    let characters = i32::try_from(text.chars().count()).unwrap_or(i32::MAX);
    if characters == 0 {
        return 0;
    }
    characters
        .saturating_mul(ADVANCE)
        .saturating_sub(1)
        .saturating_mul(scale)
}

/// Height in pixels of one line of text drawn at `scale`.
pub const fn text_height(scale: i32) -> i32 {
    GLYPH_ROWS * scale
}

/// A white RGB canvas that encodes itself as a PNG.
pub struct Canvas {
    width: usize,
    height: usize,
    pixels: Vec<u8>,
}

impl Canvas {
    /// One opaque white canvas.
    pub fn new(width: usize, height: usize) -> Self {
        Self {
            width,
            height,
            pixels: vec![0xFF; width * height * CHANNELS],
        }
    }

    /// Paint one pixel, ignoring coordinates outside the canvas.
    fn set(&mut self, x: i32, y: i32, color: Color) {
        let (Ok(column), Ok(row)) = (usize::try_from(x), usize::try_from(y)) else {
            return;
        };
        if column >= self.width || row >= self.height {
            return;
        }
        let start = (row * self.width + column) * CHANNELS;
        self.pixels[start..start + CHANNELS].copy_from_slice(&color);
    }

    /// Draw one Bresenham line between two device points.
    pub fn line(&mut self, from: (i32, i32), to: (i32, i32), color: Color) {
        let (mut x, mut y) = from;
        let step_x = if from.0 < to.0 { 1 } else { -1 };
        let step_y = if from.1 < to.1 { 1 } else { -1 };
        let width = (to.0 - x).abs();
        let height = -(to.1 - y).abs();
        let mut error = width + height;
        loop {
            self.set(x, y, color);
            if x == to.0 && y == to.1 {
                return;
            }
            let doubled = error * 2;
            if doubled >= height {
                error += height;
                x += step_x;
            }
            if doubled <= width {
                error += width;
                y += step_y;
            }
        }
    }

    /// Draw one filled disc, the marker every plotted point carries.
    pub fn disc(&mut self, center: (i32, i32), radius: i32, color: Color) {
        for offset_y in -radius..=radius {
            for offset_x in -radius..=radius {
                if offset_x * offset_x + offset_y * offset_y <= radius * radius {
                    self.set(center.0 + offset_x, center.1 + offset_y, color);
                }
            }
        }
    }

    /// Draw one line of text with its top-left corner at `origin`.
    pub fn text(&mut self, origin: (i32, i32), text: &str, scale: i32, color: Color) {
        for (index, character) in text.chars().enumerate() {
            let advance = i32::try_from(index).unwrap_or(i32::MAX) * ADVANCE * scale;
            self.glyph(
                (origin.0 + advance, origin.1),
                glyph(character),
                scale,
                color,
            );
        }
    }

    /// Paint one glyph's set bits as `scale` by `scale` blocks.
    fn glyph(&mut self, origin: (i32, i32), glyph: Glyph, scale: i32, color: Color) {
        for (row, bits) in glyph.into_iter().enumerate() {
            let top = origin.1 + i32::try_from(row).unwrap_or(0) * scale;
            for column in 0..GLYPH_WIDTH {
                if bits & (1 << (GLYPH_WIDTH - 1 - column)) == 0 {
                    continue;
                }
                let left = origin.0 + column * scale;
                for offset_y in 0..scale {
                    for offset_x in 0..scale {
                        self.set(left + offset_x, top + offset_y, color);
                    }
                }
            }
        }
    }

    /// Encode the canvas as a truecolor PNG.
    ///
    /// # Panics
    ///
    /// Panics when the canvas is larger than PNG's `u32` dimension fields.
    pub fn into_png(self) -> Vec<u8> {
        let width = u32::try_from(self.width).expect("canvas width fits in a PNG dimension");
        let height = u32::try_from(self.height).expect("canvas height fits in a PNG dimension");
        let mut header = Vec::with_capacity(13);
        header.extend_from_slice(&width.to_be_bytes());
        header.extend_from_slice(&height.to_be_bytes());
        // Eight bits per sample, truecolor RGB, deflate, adaptive filtering, no
        // interlacing: the only combination this encoder emits.
        header.extend_from_slice(&[8, 2, 0, 0, 0]);
        let mut png = Vec::from(b"\x89PNG\r\n\x1a\n");
        chunk(*b"IHDR", &header, &mut png);
        chunk(*b"IDAT", &self.compressed_scanlines(), &mut png);
        chunk(*b"IEND", &[], &mut png);
        png
    }

    /// Deflate the filter-prefixed scanlines into one zlib stream.
    fn compressed_scanlines(&self) -> Vec<u8> {
        let stride = self.width * CHANNELS;
        let mut raw = Vec::with_capacity((stride + 1) * self.height);
        for row in self.pixels.chunks(stride) {
            // Filter type 0: the rows are already tiny once deflated.
            raw.push(0);
            raw.extend_from_slice(row);
        }
        let mut encoder = ZlibEncoder::new(Vec::new(), Compression::default());
        // The sink is an in-memory `Vec`, so neither call can report an error.
        encoder
            .write_all(&raw)
            .and_then(|()| encoder.finish())
            .unwrap_or_default()
    }
}

/// Append one length-prefixed, CRC-suffixed PNG chunk.
fn chunk(kind: [u8; 4], data: &[u8], out: &mut Vec<u8>) {
    let length = u32::try_from(data.len()).unwrap_or(u32::MAX);
    out.extend_from_slice(&length.to_be_bytes());
    let start = out.len();
    out.extend_from_slice(&kind);
    out.extend_from_slice(data);
    let checksum = crc32(&out[start..]);
    out.extend_from_slice(&checksum.to_be_bytes());
}

/// The PNG chunk CRC: the standard reflected CRC-32 over type and data.
fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = 0xFFFF_FFFF_u32;
    for byte in bytes {
        crc ^= u32::from(*byte);
        for _bit in 0..8 {
            let carry = crc & 1;
            crc >>= 1;
            if carry != 0 {
                crc ^= 0xEDB8_8320;
            }
        }
    }
    !crc
}
