// ZeroS boot animation frames, design B1 "orbit" (chosen 24 October 2026):
// a white ring, a red dot orbiting it clockwise, and the ZeroS wordmark with
// its "oS" in red (option C, chosen 25 October 2026: reads as "Zero OS").
//
//   swift make-frames.swift <Roboto variable TTF> <output dir>
//
// Writes <out>/part0 (intro, played once) and <out>/part1 (one orbit, looped
// until boot completes) as PNG frames, and <out>/desc.txt. The loop is
// seamless: its first frame continues where the intro ends, and its last
// frame leads into its first. Android fades part1 out over 12 frames when
// boot finishes.
//
// SPDX-License-Identifier: Apache-2.0

import CoreGraphics
import CoreText
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 3 else {
    print("usage: swift make-frames.swift <Roboto variable TTF> <output dir>")
    exit(2)
}
let fontPath = args[1]
let outDir = URL(fileURLWithPath: args[2])

// Canvas, centred by Android on a black screen (1080x2340 on ginkgo)
let W = 520, H = 640, fps = 30
let introFrames = 36            // 1.2 s
let loopFrames = 66             // 2.2 s per orbit
let fadeFrames = 12             // Android's fade-out when boot completes

// Geometry, in top-left coordinates
let ringCenterY: CGFloat = 230, ringR: CGFloat = 150, ringWidth: CGFloat = 10
let dotR: CGFloat = 17
let wordmark = "ZeroS", wordmarkSize: CGFloat = 68, wordmarkWeight = 500.0
let wordmarkBaselineY: CGFloat = 520, wordmarkKern: CGFloat = 3
let redLetters = [3, 4]          // "o" and "S" of ZeroS

let white = CGColor(srgbRed: 0xf2 / 255, green: 0xf2 / 255, blue: 0xf0 / 255, alpha: 1)
let red = CGColor(srgbRed: 0xe5 / 255, green: 0x32 / 255, blue: 0x2d / 255, alpha: 1)
let black = CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 1)

// Roboto at weight 500 from the variable font
let descriptors = CTFontManagerCreateFontDescriptorsFromURL(URL(fileURLWithPath: fontPath) as CFURL) as! [CTFontDescriptor]
let wght = 0x7767_6874 // 'wght'
let weighted = CTFontDescriptorCreateCopyWithVariation(descriptors[0], NSNumber(value: wght), CGFloat(wordmarkWeight))
let font = CTFontCreateWithFontDescriptor(weighted, wordmarkSize, nil)

func smoothstep(_ a: Double, _ b: Double, _ x: Double) -> CGFloat {
    let t = min(max((x - a) / (b - a), 0), 1)
    return CGFloat(t * t * (3 - 2 * t))
}

func frame(ringAlpha: CGFloat, dotAlpha: CGFloat, angleDeg: Double, textAlpha: CGFloat, to url: URL) {
    let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(black)
    ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    // Core Graphics uses bottom-left coordinates
    let cx = CGFloat(W) / 2, cy = CGFloat(H) - ringCenterY
    ctx.setStrokeColor(white.copy(alpha: ringAlpha)!)
    ctx.setLineWidth(ringWidth)
    ctx.strokeEllipse(in: CGRect(x: cx - ringR, y: cy - ringR, width: 2 * ringR, height: 2 * ringR))
    // Angle clockwise from the top of the ring
    let a = angleDeg * .pi / 180
    let px = cx + ringR * CGFloat(sin(a)), py = cy + ringR * CGFloat(cos(a))
    ctx.setFillColor(red.copy(alpha: dotAlpha)!)
    ctx.fillEllipse(in: CGRect(x: px - dotR, y: py - dotR, width: 2 * dotR, height: 2 * dotR))
    let attrs: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): white.copy(alpha: textAlpha)!,
        NSAttributedString.Key(kCTKernAttributeName as String): wordmarkKern,
    ]
    let text = NSMutableAttributedString(string: wordmark, attributes: attrs)
    for index in redLetters {
        text.addAttribute(NSAttributedString.Key(kCTForegroundColorAttributeName as String),
                          value: red.copy(alpha: textAlpha)!, range: NSRange(location: index, length: 1))
    }
    let line = CTLineCreateWithAttributedString(text)
    let width = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil)) - wordmarkKern
    ctx.textPosition = CGPoint(x: (CGFloat(W) - width) / 2, y: CGFloat(H) - wordmarkBaselineY)
    CTLineDraw(line, ctx)
    let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    CGImageDestinationFinalize(dest)
}

let step = 360.0 / Double(loopFrames)
let fm = FileManager.default
for part in ["part0", "part1"] {
    try? fm.removeItem(at: outDir.appendingPathComponent(part))
    try! fm.createDirectory(at: outDir.appendingPathComponent(part), withIntermediateDirectories: true)
}
for i in 0..<introFrames {
    let x = Double(i)
    frame(ringAlpha: smoothstep(0, 14, x), dotAlpha: smoothstep(4, 14, x), angleDeg: x * step,
          textAlpha: smoothstep(10, Double(introFrames - 1), x),
          to: outDir.appendingPathComponent(String(format: "part0/%05d.png", i)))
}
for j in 0..<loopFrames {
    frame(ringAlpha: 1, dotAlpha: 1, angleDeg: Double(introFrames + j) * step, textAlpha: 1,
          to: outDir.appendingPathComponent(String(format: "part1/%05d.png", j)))
}
let desc = "\(W) \(H) \(fps)\nc 1 0 part0\np 0 0 part1 \(fadeFrames)\n"
try! desc.write(to: outDir.appendingPathComponent("desc.txt"), atomically: true, encoding: .utf8)
print("wrote \(introFrames) intro and \(loopFrames) loop frames, \(W)x\(H) at \(fps) fps")
