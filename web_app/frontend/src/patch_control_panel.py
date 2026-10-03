import re

with open("components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Find index of "{/* Strategy List */}"
idx = content.find("{/* Strategy List */}")
if idx != -1:
    # We want to keep everything before idx
    # and just close the root div
    before = content[:idx]
    after = """        </div>
    );
};

export default ControlPanel;
"""
    content = before + after

with open("components/ControlPanel.tsx", "w") as f:
    f.write(content)
