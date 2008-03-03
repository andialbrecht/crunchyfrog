from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Punctuation


# Style for Pygments source highlighter
class ApydiaDefaultStyle(Style):
    default_style = ""
    styles = {
        Comment:        "italic #999",
        Keyword:        "#00C",
        Name:           "#000",
        Name.Function:  "#F80",
        Name.Class:     "#F80",
        String:         "bg:#F8F8F8 #444",
        Punctuation:    "#444",
        Operator:       "#F80",
        Error:          "bg:#FFFFFF border:#F04 #802"
    }

