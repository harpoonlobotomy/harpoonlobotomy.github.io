---
title: LSMG files - parsed and usable. 
date: 2025-07-15
layout: post
categories:
  - scripts
  - materials

---
[Actually posted 25/7/25; I spent a bit longer making more complex scripts for this branch of the project.)

I'm not sure how well-known this is, but:

LSMG files can be used to recreate the nodetrees that all Material LSF files use as templates.

[The following are all my on observations; I don't have any Larian contacts or insider info, I was just curious and it was a fun mystery.]

Each material LSF file references a 'SourceFile', which is another LSF that contains parameters, but not in a way that can be used to replicate the nodegraph; it still relies on existing infrastructure.
But, that file name is shared with an LSMG file produced for the Material Editor. This LSMG file enables a full recreation of a template nodegraph with sufficient parsing.
I believe the original nodegraph was created in Unreal Engine, or some sibling to it; the nodegroups are primarily native to that environment.
I imagine the API exists to recreate the nodegraph in Unreal with more ease than I've encountered recreating it in Blender, if only because the required nodes will be found natively, but either way, the data is there.

LSMG is a proprietary form of XML file, although the encoding makes it difficult to parse by usual XML parsing methods - I'm sure this is conquerable, but I just fell back to line by line text parsing.

LSMG files are formed in the structure of Node [parameters] > Connections > Node [parameters], with IDs for each node, connection and connector.
The connections are layered, with some nodes having internal connections, which made the initial understanding a bit difficult I will admit.

Once parsed, it's entirely possible to give this parsed file to Blender and recreate the node tree with accurate placement, names, parameters, node types and so on.
That node tree can then be used as the template for a material, as it has all the names and associations that material expects.

This post could be longer, but I've been distracted building a complete set of scripts that will take a raw LSMG file and produce a JSON that Blender can reliably use to recreate nodegroups.
It's all routed through a wrapper script, so even though there are 5 scripts involved, the wrapper gets from raw>final by itself. I've added these scripts (and the companion files required to make it ready for blender-integration later) to the distro.

Also as a sideline - LSMG files are funtionally UE4 material nodegraphs. So perhaps I could use this to import UE4 materials into blender, far more broadly than just BG3.  Just a thought. UE4>Blender pipeline, perhaps?

Hope this is helpful to someone out here.

-Harpoon
