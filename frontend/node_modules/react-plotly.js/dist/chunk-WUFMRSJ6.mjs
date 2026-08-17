// src/factory.js
import React, { forwardRef, useCallback, useEffect, useRef } from "react";

// src/events.js
var events = [
  { name: "AfterExport" },
  { name: "AfterPlot" },
  { name: "Animated", triggersUpdate: true },
  { name: "Animating" },
  { name: "AnimatingFrame" },
  { name: "AnimationInterrupted" },
  { name: "AutoSize" },
  { name: "BeforeExport" },
  { name: "BeforeHover" },
  { name: "BeforePlot" },
  { name: "ButtonClicked" },
  { name: "Click" },
  { name: "ClickAnnotation" },
  { name: "Deselect" },
  { name: "DoubleClick", triggersUpdate: true },
  { name: "Framework" },
  { name: "Hover" },
  { name: "IcicleClick" },
  { name: "LegendClick" },
  { name: "LegendDoubleClick" },
  { name: "LegendTitleClick" },
  { name: "LegendTitleDoubleClick" },
  { name: "Relayout", triggersUpdate: true },
  { name: "Relayouting", triggersUpdate: true },
  { name: "Restyle", triggersUpdate: true },
  { name: "Redraw", triggersUpdate: true },
  { name: "Selected" },
  { name: "Selecting" },
  { name: "SliderChange" },
  { name: "SliderEnd" },
  { name: "SliderStart" },
  { name: "SunburstClick" },
  { name: "Transitioned" },
  { name: "Transitioning" },
  { name: "TransitionInterrupted" },
  { name: "TreemapClick" },
  { name: "Unhover" },
  { name: "WebGlContextLost" }
];
function getPlotlyEventName(eventName) {
  return "plotly_" + eventName.toLowerCase();
}
function getPropName(eventName) {
  return "on" + eventName;
}
var eventNames = events.map((event) => event.name);
var updateEvents = events.filter((event) => event.triggersUpdate).map((event) => getPlotlyEventName(event.name));

// src/factory.js
var isBrowser = typeof window !== "undefined";
var DEFAULT_DATA = Object.freeze([]);
var DEFAULT_STYLE = Object.freeze({ position: "relative", display: "inline-block" });
function plotComponentFactory(Plotly) {
  return forwardRef(function PlotlyComponent({
    data = DEFAULT_DATA,
    layout,
    config,
    frames,
    revision,
    onInitialized,
    onUpdate,
    onPurge,
    onError,
    debug = false,
    style = DEFAULT_STYLE,
    className,
    useResizeHandler = false,
    divId,
    ...eventProps
  }, forwardedRef) {
    const elRef = useRef(null);
    const promiseRef = useRef(Promise.resolve());
    const handlersRef = useRef({});
    const resizeHandlerRef = useRef(null);
    const unmountingRef = useRef(false);
    const prevRef = useRef(null);
    const onUpdateRef = useRef(onUpdate);
    onUpdateRef.current = onUpdate;
    const onPurgeRef = useRef(onPurge);
    onPurgeRef.current = onPurge;
    const handleUpdate = useRef(() => {
      const cb = onUpdateRef.current;
      if (typeof cb !== "function" || !elRef.current) {
        return;
      }
      const el = elRef.current;
      const frames2 = el._transitionData ? el._transitionData._frames : null;
      cb({ data: el.data, layout: el.layout, frames: frames2 }, el);
    }).current;
    const setRef = useCallback(
      (el) => {
        elRef.current = el;
        if (typeof forwardedRef === "function") {
          forwardedRef(el);
        } else if (forwardedRef) {
          forwardedRef.current = el;
        }
        if (debug && isBrowser && el) {
          window.gd = el;
        }
      },
      [forwardedRef, debug]
    );
    useEffect(() => {
      unmountingRef.current = false;
      if (prevRef.current === null) {
        prevRef.current = { data, layout, config, frames, revision };
        runPlotlyReact(true, onInitialized, true);
        return;
      }
      const prev = prevRef.current;
      const numPrev = prev.frames && prev.frames.length ? prev.frames.length : 0;
      const numNext = frames && frames.length ? frames.length : 0;
      const figureChanged = !(prev.layout === layout && prev.data === data && prev.config === config && numPrev === numNext);
      const revisionWasDefined = prev.revision !== void 0;
      const revisionChanged = prev.revision !== revision;
      prevRef.current = { data, layout, config, frames, revision };
      if (!figureChanged && (!revisionWasDefined || !revisionChanged)) {
        return;
      }
      runPlotlyReact(false, onUpdate, false);
    });
    useEffect(() => {
      const el = elRef.current;
      return () => {
        unmountingRef.current = true;
        if (el) {
          if (typeof onPurgeRef.current === "function") {
            const frames2 = el._transitionData ? el._transitionData._frames : null;
            onPurgeRef.current({ data: el.data, layout: el.layout, frames: frames2 }, el);
          }
          if (el.removeListener) {
            updateEvents.forEach((evt) => el.removeListener(evt, handleUpdate));
          }
          Plotly.purge(el);
        }
        if (resizeHandlerRef.current && isBrowser) {
          window.removeEventListener("resize", resizeHandlerRef.current);
          resizeHandlerRef.current = null;
        }
        prevRef.current = null;
        promiseRef.current = Promise.resolve();
        handlersRef.current = {};
      };
    }, []);
    function runPlotlyReact(shouldInvokeResize, figureCallback, shouldAttachUpdateEvents) {
      promiseRef.current = promiseRef.current.then(() => {
        if (unmountingRef.current) {
          return void 0;
        }
        if (!elRef.current) {
          throw new Error("Missing element reference");
        }
        return Plotly.react(elRef.current, { data, layout, config, frames });
      }).then(() => {
        if (unmountingRef.current) {
          return;
        }
        syncWindowResize(shouldInvokeResize);
        syncEventHandlers();
        invokeFigureCallback(figureCallback);
        if (shouldAttachUpdateEvents) {
          attachUpdateEvents();
        }
      }).catch((err) => {
        if (typeof onError === "function") {
          onError(err);
        }
      });
    }
    function invokeFigureCallback(callback) {
      if (typeof callback !== "function" || !elRef.current) {
        return;
      }
      const el = elRef.current;
      const f = el._transitionData ? el._transitionData._frames : null;
      callback({ data: el.data, layout: el.layout, frames: f }, el);
    }
    function attachUpdateEvents() {
      if (!elRef.current || !elRef.current.removeListener) {
        return;
      }
      updateEvents.forEach((evt) => elRef.current.on(evt, handleUpdate));
    }
    function syncWindowResize(invoke) {
      if (!isBrowser) {
        return;
      }
      if (useResizeHandler && !resizeHandlerRef.current) {
        resizeHandlerRef.current = () => Plotly.Plots.resize(elRef.current);
        window.addEventListener("resize", resizeHandlerRef.current);
        if (invoke) {
          resizeHandlerRef.current();
        }
      } else if (!useResizeHandler && resizeHandlerRef.current) {
        window.removeEventListener("resize", resizeHandlerRef.current);
        resizeHandlerRef.current = null;
      }
    }
    function syncEventHandlers() {
      eventNames.forEach((eventName) => {
        const prop = eventProps[getPropName(eventName)];
        const handler = handlersRef.current[eventName];
        const hasHandler = Boolean(handler);
        if (prop && !hasHandler) {
          addEventHandler(eventName, prop);
        } else if (!prop && hasHandler) {
          removeEventHandler(eventName);
        } else if (prop && hasHandler && prop !== handler) {
          removeEventHandler(eventName);
          addEventHandler(eventName, prop);
        }
      });
    }
    function addEventHandler(eventName, prop) {
      handlersRef.current[eventName] = prop;
      elRef.current.on(getPlotlyEventName(eventName), prop);
    }
    function removeEventHandler(eventName) {
      elRef.current.removeListener(getPlotlyEventName(eventName), handlersRef.current[eventName]);
      delete handlersRef.current[eventName];
    }
    return /* @__PURE__ */ React.createElement("div", { id: divId, style, ref: setRef, className });
  });
}

export {
  plotComponentFactory
};
//# sourceMappingURL=chunk-WUFMRSJ6.mjs.map