```mermaid
%%{ init: { 'flowchart': { 'curve': 'monotoneX' } } }%%
graph LR;
Launch_Telemetry_Producer[fa:fa-rocket Launch Telemetry Producer &#8205] --> launch-telemetry{{ fa:fa-arrow-right-arrow-left launch-telemetry &#8205}}:::topic;
launch-telemetry{{ fa:fa-arrow-right-arrow-left launch-telemetry &#8205}}:::topic --> Position_XY_calculation[fa:fa-rocket Position XY calculation &#8205];
Position_XY_calculation[fa:fa-rocket Position XY calculation &#8205] --> launch-telemetry-xy{{ fa:fa-arrow-right-arrow-left launch-telemetry-xy &#8205}}:::topic;
launch-telemetry-xy{{ fa:fa-arrow-right-arrow-left launch-telemetry-xy &#8205}}:::topic --> Rocket_visualizer[fa:fa-rocket Rocket visualizer &#8205];
f1-data{{ fa:fa-arrow-right-arrow-left f1-data &#8205}}:::topic --> starter-visualization[fa:fa-rocket starter-visualization &#8205];


classDef default font-size:110%;
classDef topic font-size:80%;
classDef topic fill:#3E89B3;
classDef topic stroke:#3E89B3;
classDef topic color:white;
```