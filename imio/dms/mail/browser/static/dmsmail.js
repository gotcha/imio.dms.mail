dmsmail = {};

dmsmail.manage_orgtype_filter = function () {
    // show org type widget only when organization type is selected
    var orgtype_widget = $(this).siblings('#orgtype_widget');
    if ($(this).find('#type_organization').prop('checked')) {
        orgtype_widget.show();
    } else {
        orgtype_widget.hide();
    }
};

dmsmail.init_batchactions_button = function () {

  var glob_sel = $('input#select_unselect_items');
  if( glob_sel[0] !== undefined && glob_sel[0].checked ) {
    glob_sel[0].checked = false;
    $('input[name="select_item"').attr('checked', false);
  }
  if ( $('.faceted-table-results')[0] == undefined ) {
    $('#dashboard-batch-actions').hide();
  }

  $('.batch-action-but').click(function (e) {
    e.preventDefault();
    var uids = selectedCheckBoxes('select_item');
    if (!uids.length) { alert('Aucun élément sélectionné'); return;}
    var referer = document.location.href.replace('#','!').replace(/&/g,'@');
    var ba_form = $(this).parent()[0];
    var form_id = ba_form.id;
    if(typeof document.batch_actions === "undefined") {
        document.batch_actions = [];
    }
    if(document.batch_actions[form_id] === undefined) {
        document.batch_actions[form_id] = ba_form.action;
    }
    ba_form.action = document.batch_actions[form_id] + '?uids=' + uids + '&referer=' + referer;
    dmsmail.initializeOverlays();
  });
};

dmsmail.initializeOverlays = function () {
    // Add batch actions popup
    $('.batch-action-form').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]'
    });
};
        
$(document).ready(function(){
    $('#faceted-form #type_widget').click(dmsmail.manage_orgtype_filter);
    $('#formfield-form-widgets-organizations .formHelp').before('<span id="pg-orga-link"><a href="contacts/plonegroup-organization">Lien vers votre organisation</a></span>');
});
