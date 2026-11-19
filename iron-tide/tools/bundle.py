#!/usr/bin/env python3
"""Build dist/iron-tide.html: the whole game in one file (for the claude.ai artifact, or to open/upload anywhere).
It talks to the live game server on iron-tide-game.netlify.app (accounts, the shared war), like the website does."""
import pathlib,re
root=pathlib.Path(__file__).resolve().parent.parent
r=lambda p:(root/p).read_text()
for f in ['js/terrain.js','js/shaders.js','js/game.js','css/style.css']:
    assert '</script' not in r(f).lower(), f
html=f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>Iron Tide</title>
<style>
{r('css/style.css')}
</style></head><body>
<canvas id="c"></canvas>
<div id="hud"><div></div></div>
<canvas id="map"></canvas>
<div id="ui"></div>
<div id="err"></div>
<div id="load">LOADING WORLD&hellip;</div>
<script id="terrainsrc" type="text/plain">{r('js/terrain.js')}</script>
<script>
{r('js/shaders.js')}
</script>
<script>
{r('js/game.js')}
</script>
</body></html>
"""
out=root/'dist'/'iron-tide.html';out.write_text(html);print(out,len(html),'bytes')
