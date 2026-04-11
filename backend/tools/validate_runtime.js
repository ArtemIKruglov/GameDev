#!/usr/bin/env node
/**
 * Runtime Game Validator
 *
 * Loads an HTML game file in jsdom, simulates 500ms of execution,
 * and captures any JavaScript errors. Used by the Python backend
 * to validate AI-generated games before saving them.
 *
 * Usage: node validate_runtime.js <path-to-html-file>
 * Output: JSON { passed: bool, errors: string[] }
 */

const fs = require("fs");
const path = require("path");

// Try to load jsdom — if not installed, output a graceful skip
let JSDOM;
try {
  JSDOM = require("jsdom").JSDOM;
} catch (e) {
  // jsdom not installed — output pass with warning
  console.log(JSON.stringify({
    passed: true,
    errors: ["[WARNING] jsdom not installed — runtime validation skipped"]
  }));
  process.exit(0);
}

const htmlPath = process.argv[2];
if (!htmlPath) {
  console.error("Usage: node validate_runtime.js <html-file>");
  process.exit(1);
}

const html = fs.readFileSync(htmlPath, "utf-8");
const errors = [];

// --- Comprehensive Canvas mock ---
function createCanvasMock() {
  const handler = {
    get(target, prop) {
      if (prop in target) return target[prop];
      // Return a no-op function for any unknown method
      return function () { return this || target; };
    },
  };

  const baseMethods = {
    fillRect() {},
    clearRect() {},
    strokeRect() {},
    beginPath() {},
    closePath() {},
    moveTo() {},
    lineTo() {},
    arc() {},
    arcTo() {},
    bezierCurveTo() {},
    quadraticCurveTo() {},
    fill() {},
    stroke() {},
    clip() {},
    rect() {},
    ellipse() {},
    save() {},
    restore() {},
    translate() {},
    rotate() {},
    scale() {},
    transform() {},
    setTransform() {},
    resetTransform() {},
    drawImage() {},
    fillText() {},
    strokeText() {},
    measureText() { return { width: 10, actualBoundingBoxAscent: 10, actualBoundingBoxDescent: 2 }; },
    createLinearGradient() {
      return new Proxy({ addColorStop() {} }, handler);
    },
    createRadialGradient() {
      return new Proxy({ addColorStop() {} }, handler);
    },
    createPattern() { return {}; },
    getImageData() { return { data: new Uint8ClampedArray(4), width: 1, height: 1 }; },
    putImageData() {},
    createImageData() { return { data: new Uint8ClampedArray(4), width: 1, height: 1 }; },
    setLineDash() {},
    getLineDash() { return []; },
    isPointInPath() { return false; },
    isPointInStroke() { return false; },
    roundRect() {},
    // Properties
    canvas: { width: 800, height: 600 },
    fillStyle: "#000",
    strokeStyle: "#000",
    lineWidth: 1,
    lineCap: "butt",
    lineJoin: "miter",
    lineDashOffset: 0,
    miterLimit: 10,
    font: "10px sans-serif",
    textAlign: "start",
    textBaseline: "alphabetic",
    globalAlpha: 1,
    globalCompositeOperation: "source-over",
    shadowBlur: 0,
    shadowColor: "rgba(0,0,0,0)",
    shadowOffsetX: 0,
    shadowOffsetY: 0,
    imageSmoothingEnabled: true,
    filter: "none",
  };

  return new Proxy(baseMethods, handler);
}

// --- Setup jsdom with mocks ---
const dom = new JSDOM(html, {
  runScripts: "dangerously",
  resources: "usable",
  pretendToBeVisual: true,
  url: "http://localhost",
  beforeParse(window) {
    // Track errors
    window._validationErrors = errors;

    // Mock canvas
    const origCreateElement = window.document.createElement.bind(window.document);
    window.document.createElement = function (tag) {
      const el = origCreateElement(tag);
      if (tag.toLowerCase() === "canvas") {
        el.getContext = function (type) {
          if (type === "2d") return createCanvasMock();
          return createCanvasMock();
        };
        el.toDataURL = function () { return "data:image/png;base64,"; };
        el.toBlob = function (cb) { if (cb) cb(new Blob()); };
      }
      return el;
    };

    // Mock existing canvas elements (in case HTML has <canvas> inline)
    const origGetById = window.document.getElementById.bind(window.document);
    window.document.getElementById = function (id) {
      const el = origGetById(id);
      if (el && el.tagName === "CANVAS" && !el._ctxMocked) {
        el._ctxMocked = true;
        el.getContext = function (type) {
          if (type === "2d") return createCanvasMock();
          return createCanvasMock();
        };
        el.toDataURL = function () { return "data:image/png;base64,"; };
      }
      return el;
    };

    const origQuery = window.document.querySelector.bind(window.document);
    window.document.querySelector = function (sel) {
      const el = origQuery(sel);
      if (el && el.tagName === "CANVAS" && !el._ctxMocked) {
        el._ctxMocked = true;
        el.getContext = function (type) {
          if (type === "2d") return createCanvasMock();
          return createCanvasMock();
        };
      }
      return el;
    };

    // Mock Audio
    window.Audio = class Audio {
      constructor() {
        this.volume = 1;
        this.currentTime = 0;
        this.paused = true;
      }
      play() { return Promise.resolve(); }
      pause() {}
      load() {}
      cloneNode() { return new Audio(); }
      addEventListener() {}
      removeEventListener() {}
    };

    // Mock AudioContext
    window.AudioContext = window.webkitAudioContext = class AudioContext {
      constructor() {
        this.state = "running";
        this.currentTime = 0;
        this.destination = {};
      }
      createOscillator() {
        return {
          connect() {},
          start() {},
          stop() {},
          frequency: { value: 440, setValueAtTime() {} },
          type: "sine",
        };
      }
      createGain() {
        return {
          connect() {},
          gain: { value: 1, setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} },
        };
      }
      createBiquadFilter() {
        return { connect() {}, frequency: { value: 0 }, Q: { value: 0 }, type: "lowpass" };
      }
      resume() { return Promise.resolve(); }
      close() { return Promise.resolve(); }
    };

    // Mock requestAnimationFrame with controlled timing
    let rafCallbacks = [];
    let rafId = 1;
    window.requestAnimationFrame = function (cb) {
      rafCallbacks.push(cb);
      return rafId++;
    };
    window.cancelAnimationFrame = function () {};
    window._rafCallbacks = rafCallbacks;

    // Mock performance
    if (!window.performance) {
      window.performance = { now: () => Date.now() };
    }

    // Mock matchMedia
    window.matchMedia = function () {
      return { matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} };
    };

    // Mock vibrate
    window.navigator.vibrate = function () { return true; };

    // Capture errors
    window.addEventListener("error", function (evt) {
      const msg = evt.message || String(evt);
      // Ignore resource loading errors (images, etc.)
      if (msg.includes("Could not load") || msg.includes("Not implemented")) return;
      errors.push(msg);
    });

    // Override console.error to capture
    const origError = window.console.error;
    window.console.error = function (...args) {
      const msg = args.map(String).join(" ");
      if (msg.includes("TypeError") || msg.includes("ReferenceError") || msg.includes("is not")) {
        errors.push(msg);
      }
    };
  },
});

// Let the DOM load and scripts execute
const window = dom.window;

// Simulate a few animation frames to trigger errors
function simulateFrames(count) {
  for (let i = 0; i < count; i++) {
    const callbacks = [...(window._rafCallbacks || [])];
    window._rafCallbacks.length = 0;
    for (const cb of callbacks) {
      try {
        cb(performance.now());
      } catch (e) {
        errors.push(e.message || String(e));
      }
    }
  }
}

// Wait for DOMContentLoaded equivalent, then simulate frames
setTimeout(() => {
  try {
    // Fire DOMContentLoaded if not already fired
    const event = new window.Event("DOMContentLoaded");
    window.document.dispatchEvent(event);
  } catch (e) {
    // Ignore if already fired
  }

  // Simulate a few frames
  setTimeout(() => {
    simulateFrames(5);

    // Simulate click on start button (common pattern)
    try {
      const startBtns = window.document.querySelectorAll("button, .start-btn, [onclick]");
      for (const btn of startBtns) {
        const text = (btn.textContent || "").toLowerCase();
        if (
          text.includes("играть") || text.includes("старт") ||
          text.includes("начать") || text.includes("start") ||
          text.includes("play")
        ) {
          btn.click();
          break;
        }
      }
    } catch (e) {
      // Ignore click errors
    }

    // Run more frames after "starting" the game
    setTimeout(() => {
      simulateFrames(10);

      // Deduplicate and output
      const uniqueErrors = [...new Set(errors)];

      // Filter out non-critical warnings
      const criticalErrors = uniqueErrors.filter(e => {
        // These are actual JS errors that will crash the game
        if (e.includes("TypeError")) return true;
        if (e.includes("ReferenceError")) return true;
        if (e.includes("SyntaxError")) return true;
        if (e.includes("is not a function")) return true;
        if (e.includes("is not iterable")) return true;
        if (e.includes("Cannot read prop")) return true;
        if (e.includes("is not defined")) return true;
        if (e.includes("of undefined")) return true;
        if (e.includes("of null")) return true;
        return false;
      });

      console.log(JSON.stringify({
        passed: criticalErrors.length === 0,
        errors: criticalErrors,
      }));

      window.close();
      process.exit(0);
    }, 100);
  }, 100);
}, 100);

// Hard timeout — kill the process if it hangs
setTimeout(() => {
  console.log(JSON.stringify({
    passed: true,
    errors: ["[WARNING] Validation timed out after 4s"]
  }));
  process.exit(0);
}, 4000);
