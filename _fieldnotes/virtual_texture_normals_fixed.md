---
title: Virtual Texture Normals - fixed!
date: 2025-06-30
layout: fieldnote
---

Chances are if you're reading this, you probably want to know how to stop your Virtual Texture normals looking like this:

<p align="center">
  <img src="{{ '/assets/images/bad-normals.jpg' | relative_url }}" alt="A collage of images of assets with very badly behaved normals." />
</p>

Okay so that's more of an interpretation of how it felt trying to get the normals to work; but for an actual example:

<p align="center">
  <img src="{{ 'assets/images
/before_and_after_pillars.webp' | relative_url }}" alt="Two carved pillars, the one on the left has bad normals, the one on the right looks quite nice." />
</p>

The one on the left uses the standard 'invert green' normal setup. The one on the right: 

Separate the Color output of the Normal image texture; invert green as usual, connecting it to the Green of a Combine Colour node.
Connect the Blue to the Blue.
Now connect the Alpha of the Normal image texture to the Red of Combine Color. 



<p align="center">
  <img src="{{ 'assets/images
/uncoloured_pillar_comparison.jpg' | relative_url }}" alt="Two carved pillars without colour applied, next to their respective Normal node trees. The one on the top/left has bad normals, the one on the bottom/right looks quite nice." />
</p>


Hope this is helpful to someone out here.

Anything specific you want to know how to do?

-Harpoon
