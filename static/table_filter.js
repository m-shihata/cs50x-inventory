function filter_items(col, id) {

    var input, filter, table, tr, td, i, txtValue;
    input = document.querySelector(id);
    filter = input.value.toUpperCase();
    table = document.querySelector("#itemsTable");
    tr = table.getElementsByTagName("tr");
    
    for (i = 0; i < tr.length; i++) {
        td = tr[i].getElementsByTagName("td")[col];
        if (td) {
            txtValue = td.textContent || td.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
                
            } else {
                tr[i].style.display = "none";
            } 
        }  
    }
}


$(function () {
    $('[data-toggle="popover"]').popover()
})
