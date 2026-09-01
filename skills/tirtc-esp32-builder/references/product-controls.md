# Product controls, reset, and power

Read this reference when the product has buttons, touch inputs, reset controls,
power keys, wake sources, or enclosure labels. Concrete pins and electrical
behavior belong in the exact board/carrier evidence and adapter, never in this
Skill.

## Identify the physical product, not just the baseboard

A retail or battery-powered device may combine a compute board with a carrier,
PMIC, latch circuit, flex PCB, or enclosure controls that are absent from the
baseboard schematic. When a user's physical observation conflicts with the
available schematic, treat it as evidence of a missing or different variant.
Do not declare a working control nonexistent. Request or inspect the exact
carrier schematic, PCB markings, photographs, BSP definitions, or safe probe
results and keep the unresolved mapping explicit.

Classify each physical label before assigning software behavior:

- MCU-readable GPIO button or touch input;
- boot-strapping input;
- reset/enable line;
- PMIC or hardware power-latch control;
- I/O-expander input;
- indicator with no input function;
- unknown control on a missing board layer.

For an MCU-readable input, record the SoC GPIO, active level, external pull,
debounce requirement, shared owner, wake capability, and any strapping role.
Holding a strapping pin during reset can select a boot mode. A reset/enable line
normally resets the MCU and cannot also be treated as an application button.
A PMIC/latch power key and an MCU “enter deep sleep” action are different
product contracts; do not substitute one for the other without circuit evidence.

## Keep controls behind a narrow adapter

Use a board/product-controls component to own GPIO setup, polling or ISR work,
debounce, gestures, and boot-held suppression. It emits bounded product intents
such as `AI_TOGGLE_REQUESTED`; it does not call TiRTC, HTTP, MQTT, media, or
session lifecycle APIs from an ISR or polling callback.

Prefer one `AI_TOGGLE_REQUESTED` event whose start/stop decision is serialized by
the state-owning runtime. If the existing runtime exposes only separate start
and stop intents, the adapter may map a public state snapshot to one of them,
but the runtime must validate the intent again against its authoritative state.
Define whether rapid gestures are queued, coalesced, or rejected so two reads of
the same stale snapshot cannot silently violate the product behavior.

The runtime remains responsible for session generation, callback ordering,
media ownership, timeouts, cleanup, and late-event rejection. A toggle must
define behavior for waiting, connecting, active, stopping, H5-owned, and
error/recovery states instead of maintaining a second Boolean inside the button
driver.

## Deterministic button behavior

For a mechanical active-low or active-high input, require all of the following:

- a stable active interval before one press event;
- no repeat event until a stable release;
- a button already held during boot must be released before it can trigger;
- short/long-press thresholds have an explicit product meaning;
- queue overflow or rejected intents are logged and recover safely;
- polling tasks and ISRs stay bounded and never block on network/session work.

Test boot-held, bounce, rapid repeated presses, press during connection, press
during active audio, press during stop, delayed SDK callbacks, and recovery to
H5 or waiting state. For a battery product, separately test cold power-on,
software shutdown/deep sleep, wake, charging/USB behavior, and reset; a passing
AI toggle does not prove the power path.

Keep debounce and gesture state transitions separable from GPIO/RTOS plumbing
so host tests can prove boot-held suppression, one event per stable press,
release re-arming, and the selected rapid-gesture policy. Add a focused runtime
test for stale or duplicate control intents whenever the runtime performs the
authoritative state validation.
