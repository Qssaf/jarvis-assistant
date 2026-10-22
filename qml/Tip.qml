import QtQuick
import QtQuick.Controls

// A tooltip in the glass style: put one inside a control and bind `visible` to its hover.
ToolTip {
    id: t
    delay: 500
    padding: 0
    contentItem: Txt { kind: "small"; text: t.text; color: Theme.text; wrapMode: Text.NoWrap; leftPadding: 10; rightPadding: 10; topPadding: 6; bottomPadding: 6 }
    background: Glass { floating: true; color: Theme.popover; radius: Theme.radiusSmall; border.color: Theme.strokeStrong }
}
