<div style="background-color: #3f3b3b; color: white; padding: 10px;\
            margin-bottom: 15px; font-family: Arial, sans-serif; font-size: 16px;\
            font-weight: bold;">${brandName}</div>
<p>Task ${task} is finished</p>
## % if ${inputName}
## <p>Your dataset ${inputName} is ready at output folder <a href="${link}">${outputName}</a>.</p>
## % endif
<p>Imaging and Visualization Group, ABCS.<p>

<div style="margin-top: 15px; border-top: 1px solid #e0e0e0; color: #999;\
            padding-top: 6px;">
  This auto-generated email sent from ${brandName} @ <a target="_blank" href="${host}">${host}</a>.
</div>
