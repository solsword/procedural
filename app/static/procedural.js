/*
 * procedural.js
 *
 * Parson's puzzles widget.
 */

//---------------//
// Drag handlers //
//---------------//

// global reference to DOM element being dragged
var DRAGGED = undefined;

// Collection of event handlers for dragging & dropping code blocks
var DRAGHANDLERS = {
  "start": function (ev) {
    if (
      ev.target.classList == undefined
   || !ev.target.classList.contains("code_block")
    ) {
      ev.preventDefault();
      return;
    }
    DRAGGED = ev.target;
    DRAGGED.style.opacity = 0.6;
    return false;
  },
  "end": function (ev) {
    if (DRAGGED) {
      DRAGGED.style.opacity = "";
    }
    ev.preventDefault();
    return false;
  },
  "enter": function (ev) {
    if (!same_widget(ev.target, DRAGGED)) { return; }
    if (
      ev.target.classList.contains("code_slot")
   || ev.target.classList.contains("code_block")
    ) {
      ev.dataTransfer.dropEffect = 'move';
      ev.target.classList.add("hovered");
    }
  },
  "leave": function (ev) {
    if (!same_widget(ev.target, DRAGGED)) { return; }
    if (
      ev.target.classList.contains("code_slot")
   || ev.target.classList.contains("code_block")
    ) {
      ev.dataTransfer.dropEffect = 'none';
      ev.target.classList.remove("hovered");
    }
  },
  "over": function (ev) {
    ev.preventDefault();
    return false;
  },
  "drop": function (ev) {
    if (!same_widget(ev.target, DRAGGED)) { return; }
    if (ev.target.classList.contains("code_slot")) {
      // drop on a slot: create a slot where we came from and replace the slot
      // that we landed on
      let slot = ev.target;
      let block = DRAGGED;
      let newslot = create_slot();
      block.parentNode.insertBefore(newslot, block);
      block.parentNode.removeChild(block);
      slot.parentNode.insertBefore(block, slot);
      slot.parentNode.removeChild(slot);
    } else if (ev.target.classList.contains("code_block")) {
      // drop on a code block: swap places with it
      let hit = ev.target;
      let block = DRAGGED;
      let hit_parent = hit.parentNode;
      let block_parent = block.parentNode;
      let block_next = block.nextSibling;
      // If we're swapping with the block after us, we need to insert that block
      // before ourselves.
      if (block_next == hit) {
        block_next = block;
      }
      block_parent.removeChild(block);
      hit_parent.insertBefore(block, hit);
      hit_parent.removeChild(hit);
      if (block_next != null) {
        block_parent.insertBefore(hit, block_next);
      } else {
        block_parent.appendChild(hit);
      }
      block.classList.remove("hovered");
      hit.classList.remove("hovered");
    }
  },
};

//--------------------------//
// DOM Management Functions //
//--------------------------//

function create_slot() {
  /*
   * Creates a new empty slot div.
   */
  let slot = document.createElement("div");
  slot.classList.add("code_slot");
  slot.innerHTML = "&nbsp;"; // don't let it be completely empty
  return slot;
}

function add_code_block_to_bucket(bucket, block) {
  /*
   * Adds a block of code to a code block bucket. Creates the requisite DOM
   * element and translates from raw code to HTML specifics. The given bucket
   * element should be a DOM element with the code_bucket class.
   */
  let codeblock = document.createElement("div");
  codeblock.classList.add("code_block");
  codeblock.innerHTML = block.replace(
    /	/g,
    '&nbsp;&nbsp;&nbsp;&nbsp;'
  );
  codeblock.draggable = "true";
  codeblock.__code__ = block;
  bucket.appendChild(codeblock);
}

function add_empty_slot_to_bucket(bucket) {
  /*
   * Adds an empty slot to a code bucket (should be a DOM element with class
   * code_bucket).
   */
  bucket.appendChild(create_slot());
}

function my_widget(node) {
  /*
   * Figure out which widget a DOM node belongs to. Recursively asks parent DOM
   * node until a node with __widget__ defined is found.
   */
  if (node.__widget__) {
    return node.__widget__;
  } else if (node.parentNode) {
    return my_widget(node.parentNode);
  } else {
    return undefined;
  }
}

function same_widget(a, b) {
  /*
   * Generic function for asking if two elements belong to the same widget or
   * not. Just uses my_widget on each and compares results.
   */
  return my_widget(a) === my_widget(b);
}

//----------------------//
// Evaluation Functions //
//----------------------//

function eval_block(block, env, language) {
  /*
   * Evaluates the given code block in the given environment, modifying that
   * environment. It returns the modified environment (or a newly-constructed
   * environment if no environment was given).
   */
  if (env == undefined) {
    env = {}; // create a new object
  }
  if (language == undefined) {
    langauge = "javascript";
  }

  if (language == "javascript") {
    return eval_js(block, env);
  } else if (language == "python") {
    return eval_py(block, env);
  }
}

function eval_js(block, env) {
  /*
   * Evaluates a block of JavaScript code in the given environment, modifying
   * it and returning the modified result.
   */
  env.console = {
    "log": function() {
      let msg = "";
      for (let arg of arguments) {
        msg += arg;
      }
      if (env.__messages__ == undefined) {
        env.__messages__ = [];
      }
      env.__messages__.push(msg);
    },
    "warn": function() {
      let msg = "";
      for (let arg of arguments) {
        msg += arg;
      }
      if (env.__warnings__ == undefined) {
        env.__warnings__ = [];
      }
      env.__warnings__.push(msg);
    },
    "error": function() {
      let msg = "";
      for (let arg of arguments) {
        msg += arg;
      }
      if (env.__errors__ == undefined) {
        env.__errors__ = [];
      }
      env.__errors__.push(msg);
    }
  };
  try {
    // TODO: Proxy magic: https://stackoverflow.com/questions/2051678/getting-all-variables-in-scope
    // TODO: or do we need ESPRIMA? https://esprima.org/index.html
    function scope() {
      console.error("JavaScript evaluation isn't implemented yet!");
      //eval("'use strict'; " + block + "}");
    }
    scope()
  } catch (e) {
    if (env.__errors__ == undefined) {
      env.__errors__ = [];
    }
    env.__errors__.push(e);
  }
  return env;
}

function eval_py(block, env) {
  /*
   * Evaluates a block of Python code in the given environment, modifying it
   * and returning the modified result.
   * TODO: Implement me using Brython!
   */
  //console.log($locals);
  /*$locals = env;*/
  console.log(block);
  /*
  let tree = __BRYTHON__.py2js(block, "__main__", "__main__");
  //let tree = __BRYTHON__.py2js(block, "__main__");
  let js = tree.to_js();
  eval(js);
  */
  __BRYTHON__.run_script(block, "__main__");
  console.log(angle, tea);
  return $locals;
  //console.error("Python evaluation isn't implemented yet!");
}

//-----------------//
// Setup functions //
//-----------------//

function setup_widget(node, puzzle) {
  /*
   * Sets up a widget as a Parson's puzzle. First argument should be a DOM div
   * with class procedural_widget, and second should be a puzzle object with
   * the following keys:
   *
   *   code: a string containing blocks of code in solved order
   *   extra (optional): distractor blocks of code
   *   language (optional): code language; defaults to JavaScript. Supported
   *     languages are:
   *     
   *       - TODO: JavaScript
   *       - TODO: Python
   */
  // TODO: Use data- properties to define what kind of widget and what the
  // puzzle is!
  if (puzzle == undefined) {
    if (node.hasAttribute("data-puzzle")) {
      try {
        puzzle = JSON.parse(node.getAttribute("data-puzzle"));
      } catch (e) {
        console.error(e);
        console.error(
          "Malformed JSON in data-puzzle attribute.",
          node.getAttribute("data-puzzle")
        );
      }
      if (puzzle != undefined) {
        setup_base_puzzle(node, puzzle.code, puzzle.extra);
      } else {
        setup_base_puzzle(node);
      }
    } else {
      setup_base_puzzle(node);
    }
  } else {
    setup_base_puzzle(node, puzzle.code, puzzle.extra);
  }

  // Set up event handlers on this widget
  node.addEventListener("dragstart", DRAGHANDLERS.start, false);
  node.addEventListener("dragend", DRAGHANDLERS.end, false);
  node.addEventListener("dragover", DRAGHANDLERS.over, false);
  node.addEventListener("dragenter", DRAGHANDLERS.enter, false);
  node.addEventListener("dragenter", DRAGHANDLERS.enter, false);
  node.addEventListener("dragleave", DRAGHANDLERS.leave, false);
  node.addEventListener("drop", DRAGHANDLERS.drop, false);
}

function setup_base_puzzle(node, code, extra) {
  /*
   * Sets up a basic two-column puzzle where you drag blocks from the left into
   * numbered slots on the right.
   */
  let w = {}; // the widget object
  node.__widget__ = w; // attach it to the DOM

  // Split code + extras into blocks, or make up stuff if it wasn't provided
  let code_blocks;
  if (code == undefined) {
    code_blocks = [
      "a = 3;",
      "b = 4;",
      "c = a*b;",
      "a += 5",
      "b = a + 1;",
      "c = c + a;"
    ];
  } else {
    code_blocks = code.split('\n');
  }
  // Filter out blank blocks:
  w.code_blocks = [];
  for (let block of code_blocks) {
    if (block.replace(/\s/g, '').length > 0) {
      w.code_blocks.push(block);
    }
  }
  let distractors;
  if (extra == undefined) {
    distractors = [];
  } else {
    distractors = extra.split('\n');
  }
  // Filter out blank blocks:
  w.distractors = [];
  for (let block of distractors) {
    if (block.replace(/\s/g, '').length > 0) {
      w.distractors.push(block);
    }
  }
  w.all_blocks = w.code_blocks.concat(w.distractors);

  // bucket for source blocks
  w.source_bucket = document.createElement("div");
  w.source_bucket.classList.add("code_bucket");
  w.source_bucket.classList.add("code_source");
  node.appendChild(w.source_bucket);

  // TODO: Scramble!

  // Add each code block to our source div:
  for (let i = 0; i < w.all_blocks.length; ++i) {
    add_code_block_to_bucket(w.source_bucket, w.all_blocks[i]);
  }

  // bucket for solution blocks
  w.soln_bucket = document.createElement("div");
  w.soln_bucket.classList.add("code_bucket");
  w.soln_bucket.classList.add("soln_list");
  node.appendChild(w.soln_bucket);

  // TODO: variable/unspecified # of answer slots?
  // Create the exact right number of slots:
  for (let i = 0; i < w.code_blocks.length; ++i) {
    add_empty_slot_to_bucket(w.soln_bucket);
  }

  let eb = document.createElement("input");
  eb.type = "button";
  eb.value = "evaluate";
  eb.__bucket__ = w.soln_bucket;
  eb.addEventListener(
    "click",
    function () {
      let bucket = eb.__bucket__;
      let code = "";
      for (let child of bucket.children) {
        if (child.hasOwnProperty("__code__")) {
          code += child.__code__ + '\n';
        }
      }
      console.log(code);
      let env = eval_block(code, undefined, "python");
      alert("" + env);
    }
  );
  w.soln_bucket.appendChild(eb);
}


function sequence_puzzles(widget, puzzles) {
  /*
   * Takes a list of puzzle objects and presents them one at a time through the
   * given widget, displaying a new puzzle when the current one is solved.
   */
  //console.log(puzzles[0]);
  setup_widget(widget, puzzles[0]);
  // TODO: HERE
}

function load_puzzles(url, continuation) {
  /*
   * Loads the given URL (a relative URL) and parses a JSON array of objects
   * which each define a puzzle. Passes the resulting array to the given
   * continuation function when the loading is done.
   *
   * See:
   * https://codepen.io/KryptoniteDove/post/load-json-file-locally-using-pure-javascript
   * Note that with Chrome --allow-file-access-from-files will be necessary if
   * not being hosted by a server.
   */
  var xobj = new XMLHttpRequest();
  xobj.overrideMimeType("application/json");
  var base = window.location.href;
  var path = base.substr(0, base.lastIndexOf('/'));
  var dpath = path + "/" + url;

  // Load asynchronously
  xobj.open("GET", dpath);
  xobj.onload = function () {
    var successful = (
      xobj.status == 200
   || (xobj.status == 0 && dpath.startsWith("file://"))
    );
    if (!successful) {
      console.error("Failed to load puzzles from: '" + url + "'");
      console.error("(XMLHTTP request failed)", xobj);
      return;
    }
    try {
      var json = JSON.parse(xobj.responseText);
      continuation(json);
    } catch (e) {
      console.error("Failed to load puzzles from: '" + url + "'");
      console.error("(JSON parsing or continuation failed)", json);
      return;
    }
  };
  xobj.onerror = function () {
    console.error("Failed to load puzzles from: '" + url + "'");
    console.error("(XMLHTTP request crashed)", xobj);
  }
  try {
    xobj.send(null);
  } catch (e) {
    console.error("Failed to load puzzles from: '" + url + "'");
    console.error("(XMLHTTP request crashed)", xobj);
  };
}

function init() {
  /*
   * Selects all procedural_widget divs and creates elements inside each one to
   * play a Parson's puzzle.
   */

  // Collect each widget:
  let widgets = document.querySelectorAll(".procedural_widget");

  // Set up each widget automatically:
  // widgets.forEach(w => setup_widget(w));

  // Sequence loaded puzzles into the first widget:
  let first = widgets[0];
  load_puzzles(
    "puzzles.json",
    puzzles => sequence_puzzles(first, puzzles)
  );
}

// Init when document loads:
window.addEventListener("load", function () { brython(); init(); });
