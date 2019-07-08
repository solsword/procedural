/*
 * procedural.js
 *
 * Parson's puzzles widget.
 */

// global reference to DOM element being dragged
var DRAGGED = undefined;

// Collection of event handlers for dragging & dropping code lines
var DRAGHANDLERS = {
  "start": function (ev) {
    if (
      ev.target.classList == undefined
   || !ev.target.classList.contains("code_line")
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
   || ev.target.classList.contains("code_line")
    ) {
      ev.dataTransfer.dropEffect = 'move';
      ev.target.classList.add("hovered");
    }
  },
  "leave": function (ev) {
    if (!same_widget(ev.target, DRAGGED)) { return; }
    if (
      ev.target.classList.contains("code_slot")
   || ev.target.classList.contains("code_line")
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
      let line = DRAGGED;
      let newslot = create_slot();
      line.parentNode.insertBefore(newslot, line);
      line.parentNode.removeChild(line);
      slot.parentNode.insertBefore(line, slot);
      slot.parentNode.removeChild(slot);
    } else if (ev.target.classList.contains("code_line")) {
      // drop on a code line: swap places with it
      let hit = ev.target;
      let line = DRAGGED;
      let hit_parent = hit.parentNode;
      let line_parent = line.parentNode;
      let line_next = line.nextSibling;
      // If we're swapping with the line after us, we need to insert that line
      // before ourselves.
      if (line_next == hit) {
        line_next = line;
      }
      line_parent.removeChild(line);
      hit_parent.insertBefore(line, hit);
      hit_parent.removeChild(hit);
      if (line_next != null) {
        line_parent.insertBefore(hit, line_next);
      } else {
        line_parent.appendChild(hit);
      }
      line.classList.remove("hovered");
      hit.classList.remove("hovered");
    }
  },
};

function create_slot() {
  /*
   * Creates a new empty slot div.
   */
  let slot = document.createElement("div");
  slot.classList.add("code_slot");
  slot.innerHTML = "&nbsp;"; // don't let it be completely empty
  return slot;
}

function setup_widget(node, puzzle) {
  /*
   * Sets up a widget as a Parson's puzzle. First argument should be a DOM div
   * with class procedural_widget, and second should be a puzzle object with
   * the following keys:
   *
   *   code: a string containing lines of code in solved order
   *   extra (optional): distractor lines of code
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
   * Sets up a basic two-column puzzle where you drag lines from the left into
   * numbered slots on the right.
   */
  let w = {}; // the widget object
  node.__widget__ = w; // attach it to the DOM

  // Split code + extras into lines, or make up stuff if it wasn't provided
  let code_lines;
  if (code == undefined) {
    code_lines = [
      "a = 3;",
      "b = 4;",
      "c = a*b;",
      "a += 5",
      "b = a + 1;",
      "c = c + a;"
    ];
  } else {
    code_lines = code.split('\n');
  }
  // Filter out blank lines:
  w.code_lines = [];
  for (let line of code_lines) {
    if (line.replace(/\s/g, '').length > 0) {
      w.code_lines.push(line);
    }
  }
  let distractors;
  if (extra == undefined) {
    distractors = [];
  } else {
    distractors = extra.split('\n');
  }
  // Filter out blank lines:
  w.distractors = [];
  for (let line of distractors) {
    if (line.replace(/\s/g, '').length > 0) {
      w.distractors.push(line);
    }
  }
  w.all_lines = w.code_lines.concat(w.distractors);

  // bucket for source lines
  w.source_bucket = document.createElement("div");
  w.source_bucket.classList.add("code_bucket");
  w.source_bucket.classList.add("code_source");
  node.appendChild(w.source_bucket);

  // TODO: Scramble!

  // Add each code line to our source div:
  for (let i = 0; i < w.all_lines.length; ++i) {
    add_code_line_to_bucket(w.source_bucket, w.all_lines[i]);
  }

  // bucket for solution lines
  w.soln_bucket = document.createElement("div");
  w.soln_bucket.classList.add("code_bucket");
  w.soln_bucket.classList.add("soln_list");
  node.appendChild(w.soln_bucket);

  // TODO: variable/unspecified # of answer slots?
  // Create the exact right number of slots:
  for (let i = 0; i < w.code_lines.length; ++i) {
    add_empty_slot_to_bucket(w.soln_bucket);
  }
}

function add_code_line_to_bucket(bucket, line) {
  /*
   * Adds a line of code to a code line bucket. Creates the requisite DOM
   * element and translates from raw code to HTML specifics. The given bucket
   * element should be a DOM element with the code_bucket class.
   */
  let codeline = document.createElement("div");
  codeline.classList.add("code_line");
  codeline.innerHTML = line.replace(
    /	/g,
    '&nbsp;&nbsp;&nbsp;&nbsp;'
  );
  codeline.draggable = "true";
  bucket.appendChild(codeline);
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
window.addEventListener("load", function () { init(); });
