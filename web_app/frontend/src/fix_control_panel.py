with open("components/ControlPanel.tsx", "r") as f:
    content = f.read()

# The clean end is right after the "Hủy Mọi Lệnh" button block closes.
# It ends with:
#                 </div>
#             </div>

search_str = "Hủy Mọi Lệnh'}\n                    </button>\n                </div>\n            </div>"
idx = content.find(search_str)

if idx != -1:
    before = content[:idx + len(search_str)]
    after = """

        </div>
    );
};

export default ControlPanel;
"""
    with open("components/ControlPanel.tsx", "w") as f:
        f.write(before + after)
