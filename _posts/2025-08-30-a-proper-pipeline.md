---
title: The Pipeline is Done (almost).
date: 2025-08-30
layout: post
categories:
  - materials

---

The BG3 matgen/tempgen (Material Generator/Template Generator) is almost entirely complete, now I'm just adding little nice-to-have improvements. With the asset(s) selected, you click a button and the scripts produce the required material, from template layout to image textures and parameter values. 

With MatGen running in Blender, clicking the 'Create Material' button will trigger the TempGen and Wrapper scripts are needed, without manual intervention to create the JSON needed for TempGen. 

Given the extensive setup required for this process (-- all texture and VT PAKs unpacked, the extensive database setup) I can't imagine this system will ever be of use to anyone but myself, but maybe some version of it will be useful to someone some day. I want to make a set of 'general templates' that one can simply apply the correct images to, to approximate general materials without needing the full setup, but Volno's Texture Toolkit exists, so I'm not sure if there's much point, really. The only thing my system has that his doesn't is tattoo selection, as he doesn't have a Flipbook node.

I'll still make it, though, even if it might be rather pointless. I didn't really have any reason to put this much time in to the project so far other than 'I wanted to see if I could', so why stop now? I've learned to code a bit through this project and learned a lot about how BG3 works under the hood, and it's been really fun. So I think it's been worthwhile, at least to me.

Hope you're all doing well out there. 

-Harpoon
