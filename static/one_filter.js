function new_filter(id_1, id_2, col_1, col_2,) {
    if (document.querySelector(id_1).value != '' || document.querySelector(id_2).value != '') { 

        document.querySelector(id_1).value = ''; 
        document.querySelector(id_2).value = ''; 
        
        filter_items(col_1, id_1); 
        filter_items(col_2, id_2);

    }
}    