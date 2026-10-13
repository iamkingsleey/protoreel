# Protoreel

**Turn HTML prototypes into smooth, frame-perfect social videos.**

Design an interaction, then let Protoreel film it. Record it yourself in the Studio, or just ask your AI assistant to do it for you. You get a polished video, ready to post.

## Features

- **Two ways to record.** Perform the interaction yourself in the Studio, or describe it to Claude, Cursor or VS Code and let it record for you.
- **Every social format.** 4:5 feed, 9:16 Reels and TikTok, 1:1 square, 16:9 landscape, and Dribbble sizes.
- **A natural cursor.** Clicks, drags and scrolls look like a real hand, not a robot.
- **Sound included.** If your prototype makes sound, it plays in the video too.
- **Re-cut in seconds.** Record once, then export the same take in any other format.

## Render quality

- **Frame-perfect.** Every frame is captured at exactly the right moment, so videos never stutter or drop frames, however fast or slow your computer is.
- **Smooth 60 fps, up to 4K.** Crisp text and edges at any size.
- **Steady motion.** Small hand shakes are smoothed out automatically.
- **Plays everywhere.** Standard MP4 that uploads cleanly to every platform.

## Get started

Works on macOS and Linux. Setup takes about five minutes, and you only do it once.

### 1. Install uv

[uv](https://docs.astral.sh/uv/) is a small, free tool that downloads and runs Protoreel for you. Open the **Terminal** app, paste this line and press Enter:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

When it finishes, close Terminal and open it again.

### 2. Set up Protoreel

```
uvx protoreel setup
```

This downloads the browser Protoreel films with and creates a **Protoreel** folder in your home folder. The first run takes a minute or two.

### 3. Add your prototype

Save your interaction as an `.html` file and put it in the Protoreel folder. Any HTML works: a page you coded, a CodePen export, or a prototype an AI built for you.

### 4. Record your video

```
uvx protoreel studio
```

The Studio opens in your browser. Then:

1. Pick your prototype from the list.
2. Choose a format, like 4:5 for the feed or 9:16 for Reels, and adjust the zoom.
3. Press **Capture** and use the prototype as you normally would.
4. Press **Esc** when you're done.
5. Press **Render**. Your video is saved in the `renders` folder inside your Protoreel folder.

From now on, step 4 is all you need: open Terminal and run `uvx protoreel studio`.

### Or let your AI record it (optional)

Using Claude Code? Run this once:

```
claude mcp add protoreel -- uvx protoreel mcp
```

Then just ask, for example: *"Record checkout.html as a 9:16 video: tap Add to bag, then open the bag."*

For Claude Desktop, Cursor and VS Code, the [guide](docs/guide.md) shows where to paste the settings that `uvx protoreel setup` prints. It also covers mobile prototypes, every format and option, and fixes for common problems.

## License

MIT © Kingsley Mkpandiok
