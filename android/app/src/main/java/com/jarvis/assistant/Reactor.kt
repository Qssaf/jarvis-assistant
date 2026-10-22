package com.jarvis.assistant

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.Dp

/** The arc reactor: halo, thin outer ring, a turning segmented ring, a solid inner ring and a glowing core.
 *  [mini] keeps only the core and inner ring (top bar, chat avatar). */
@Composable
fun Reactor(size: Dp, working: Boolean = false, dim: Boolean = false, mini: Boolean = false, modifier: Modifier = Modifier) {
    val color by animateColorAsState(if (working) J.warm else if (dim) J.text3 else J.accent, tween(400), label = "reactor")
    var angle by remember { mutableFloatStateOf(0f) }
    val period by rememberUpdatedState(if (working) 3f else 14f)
    if (!mini) LaunchedEffect(Unit) {
        var last = 0L
        while (true) withFrameNanos { now ->
            if (last != 0L) angle = (angle + 360f * (now - last) / 1e9f / period) % 360f
            last = now
        }
    }
    val breath by rememberInfiniteTransition(label = "breath").animateFloat(1f, 1.03f,
        infiniteRepeatable(tween(1500, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "breath")
    Canvas(modifier.size(size)) {
        val c = center
        val r = this.size.minDimension / 2
        if (mini) {
            drawCircle(Brush.radialGradient(listOf(color.copy(alpha = 0.35f), Color.Transparent), c, r), r, c)
            drawCircle(color, r * 0.8f, c, style = Stroke(r * 0.1f))
            drawCircle(Brush.radialGradient(0f to Color.White, 0.3f to Color.White, 1f to color, center = c, radius = r * 0.55f), r * 0.55f, c)
            return@Canvas
        }
        drawCircle(Brush.radialGradient(listOf(color.copy(alpha = 0.25f), color.copy(alpha = 0.08f), Color.Transparent), c, r), r, c)
        drawCircle(color.copy(alpha = 0.3f), r * 0.66f, c, style = Stroke(1.2f * density))
        // the segmented ring: 10 arcs
        val seg = r * 0.56f
        rotate(angle, c) {
            for (i in 0 until 10) drawArc(color.copy(alpha = 0.7f), i * 36f + 4f, 28f, false, Offset(c.x - seg, c.y - seg), Size(seg * 2, seg * 2),
                style = Stroke(r * 0.055f, cap = StrokeCap.Butt))
        }
        drawCircle(color.copy(alpha = 0.9f), r * 0.38f, c, style = Stroke(2f * density))
        val core = r * 0.28f * breath
        drawCircle(Brush.radialGradient(listOf(color.copy(alpha = 0.55f), Color.Transparent), c, core * 1.9f), core * 1.9f, c)
        drawCircle(Brush.radialGradient(0f to Color.White, 0.22f to Color.White, 0.55f to J.listen, 1f to color, center = c, radius = core), core, c)
    }
}

/** The canvas every screen sits on: a deep navy gradient lit by a soft state-coloured glow top right and a warm one bottom left. */
@Composable
fun Backdrop(working: Boolean, modifier: Modifier = Modifier, content: @Composable BoxScope.() -> Unit) {
    // (a lighter amber at lower alpha while working: J.warm at the cyan's alpha reads as a brown stain)
    val glow by animateColorAsState(if (working) Color(0x17FFB86B) else J.accent.copy(alpha = 0.13f), tween(600), label = "glow")
    Box(modifier.fillMaxSize()) {
        Canvas(Modifier.fillMaxSize()) {
            drawRect(Brush.verticalGradient(listOf(J.bgTop, J.bg, J.bgBottom)))
            val w = size.width
            val h = size.height
            drawCircle(Brush.radialGradient(listOf(glow, Color.Transparent), Offset(w * 0.95f, h * 0.02f), w * 1.0f), w * 1.0f, Offset(w * 0.95f, h * 0.02f))
            drawCircle(Brush.radialGradient(listOf(J.warm.copy(alpha = 0.035f), Color.Transparent), Offset(0f, h * 0.95f), w * 0.7f), w * 0.7f, Offset(0f, h * 0.95f))
        }
        content()
    }
}
