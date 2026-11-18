var _____WB$wombat$assign$function_____=function(name){return (globalThis._wb_wombat && globalThis._wb_wombat.local_init && globalThis._wb_wombat.local_init(name))||globalThis[name];};if(!globalThis.__WB_pmw){globalThis.__WB_pmw=function(obj){this.__WB_source=obj;return this;}}{
let window = _____WB$wombat$assign$function_____("window");
let self = _____WB$wombat$assign$function_____("self");
let document = _____WB$wombat$assign$function_____("document");
let location = _____WB$wombat$assign$function_____("location");
let top = _____WB$wombat$assign$function_____("top");
let parent = _____WB$wombat$assign$function_____("parent");
let frames = _____WB$wombat$assign$function_____("frames");
let opener = _____WB$wombat$assign$function_____("opener");
/*!
 * jQuery UI Touch Punch 0.2.3
 *
 * Copyright 2011–2014, Dave Furfero
 * Dual licensed under the MIT or GPL Version 2 licenses.
 *
 * Depends:
 *  jquery.ui.widget.js
 *  jquery.ui.mouse.js
 */
!function(a){function f(a,b){if(!(a.originalEvent.touches.length>1)){a.preventDefault();var c=a.originalEvent.changedTouches[0],d=document.createEvent("MouseEvents");d.initMouseEvent(b,!0,!0,window,1,c.screenX,c.screenY,c.clientX,c.clientY,!1,!1,!1,!1,0,null),a.target.dispatchEvent(d)}}if(a.support.touch="ontouchend"in document,a.support.touch){var e,b=a.ui.mouse.prototype,c=b._mouseInit,d=b._mouseDestroy;b._touchStart=function(a){var b=this;!e&&b._mouseCapture(a.originalEvent.changedTouches[0])&&(e=!0,b._touchMoved=!1,f(a,"mouseover"),f(a,"mousemove"),f(a,"mousedown"))},b._touchMove=function(a){e&&(this._touchMoved=!0,f(a,"mousemove"))},b._touchEnd=function(a){e&&(f(a,"mouseup"),f(a,"mouseout"),this._touchMoved||f(a,"click"),e=!1)},b._mouseInit=function(){var b=this;b.element.bind({touchstart:a.proxy(b,"_touchStart"),touchmove:a.proxy(b,"_touchMove"),touchend:a.proxy(b,"_touchEnd")}),c.call(b)},b._mouseDestroy=function(){var b=this;b.element.unbind({touchstart:a.proxy(b,"_touchStart"),touchmove:a.proxy(b,"_touchMove"),touchend:a.proxy(b,"_touchEnd")}),d.call(b)}}}(jQuery);

jQuery(document).ready(function($) {


    /*======= Skillset *=======*/
    $('.level-bar-inner').css('height', '30');
    $('.level-bar-inner').css('width', '0');
    
    $(window).on('load', function() {

        $('.level-bar-inner').each(function() {
        
            var itemWidth = $(this).data('level');
            
            $(this).animate({
                width: itemWidth
            }, 800);
            
        });

    });
    
    $('#rootwizard').bootstrapWizard({        
        onNext: function(tab, navigation, index) {
            //alert('Jack is a dull boy');
        },
        onTabShow: function(tab, navigation, index) {
        var $total = navigation.find('li').length;
        var $current = index+1;
        var $percent = ($current/$total) * 100;
        
        // If it's the last tab then hide the last button and show the finish instead
        if($current >= $total) {
            $('#rootwizard').find('.pager .next').hide();
            $('#rootwizard').find('.pager .finish').show();
            $('#rootwizard').find('.pager .finish').removeClass('disabled');
        } else {
            $('#rootwizard').find('.pager .next').show();
            $('#rootwizard').find('.pager .finish').hide();
        }        
    }
    });
    $('#rootwizard .finish').click(function() {
        var myArray = [];

        $('.list-group-item').each(function(index, elem) {
            myArray.push([$(elem).index(), $(elem).attr('data-type')]);
        });

        //alert('Submiting the results!');
        var data = {
          "action": "count",
          "payload": myArray
        };
        data = $(this).serialize() + "&" + $.param(data);
        $.ajax({
          type: "POST",
          dataType: "json",
          url: "process.php", //Relative or absolute path to response.php file
          data: data,
          success: function(data) {
            /*$(".the-return").html(
              "Favorite beverage: " + data["favorite_beverage"] + "<br />Favorite restaurant: " + data["favorite_restaurant"] + "<br />Gender: " + data["gender"] + "<br />JSON: " + data["json"]
            );*/

            //alert("Form submitted successfully.\nReturned json: " + data['d'] + ", " + data['i'] + ", " + data['s'] + ", " + data['c']);
            $("#d").text(data['d']);
            $("#i").text(data['i']);
            $("#s").text(data['s']);
            $("#c").text(data['c']);
            var a = "D:" +data['d'] + ", I:" + data['i'] + ", S:" + data['s'] + ", C:" + data['c'];
            $("#test_results").val(a);
            $('#mail_link').attr('href','mailto:school@stratoplan.ru?subject=Я%20прошел%20DISC&body=Мой%20результат%20DISC-теста:%20'+a);
          }
        });
        
        $('#wizardmodal').modal('hide');
        $('#results').modal('show');
        return false;
        
    });

    var panelList = $('.list-group');

    panelList.sortable({
        // Only make the .panel-heading child elements support dragging.
        // Omit this to make the entire <li>...</li> draggable.
        // handle: '.panel-heading', 
        update: function() {
            $('.list-group-item', panelList).each(function(index, elem) {
                
                 var $listItem = $(elem),
                     newIndex = $listItem.index();

                     //console.log($(this).parent().attr("id") + " - " + $listItem.index() + " - " + $(elem).attr('data-type'));
                 // Persist the new indices.
            });
        }
    });
    $('#test_results').click(function () {
        this.select();
    });
    $('#test_results').focus(function () {
        this.select();
    });
});
}

/*
     FILE ARCHIVED ON 06:59:18 Dec 15, 2025 AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON 20:46:21 Nov 15, 2026.
     JAVASCRIPT APPENDED BY WAYBACK MACHINE, COPYRIGHT INTERNET ARCHIVE.

     ALL OTHER CONTENT MAY ALSO BE PROTECTED BY COPYRIGHT (17 U.S.C.
     SECTION 108(a)(3)).
*/
/*
playback timings (ms):
  captures_list: 0.582
  exclusion.robots: 0.057
  exclusion.robots.policy: 0.045
  esindex: 0.008
  cdx.remote: 33.723
  LoadShardBlock: 259.113 (3)
  PetaboxLoader3.resolve: 121.939 (3)
  PetaboxLoader3.datanode: 316.292 (4)
  load_resource: 248.328
*/