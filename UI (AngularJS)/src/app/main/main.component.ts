import { Component, OnInit } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ResourceService } from '../services/resource.service';
import { v4 as uuidv4 } from 'uuid';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss']
})
export class MainComponent implements OnInit {
  form: FormGroup;

  public plants2: Array<any>;

  constructor(private resourceService: ResourceService) {
    this.form = new FormGroup({
      id: new FormControl(uuidv4()),
      name: new FormControl('', Validators.compose([
        Validators.required,
        Validators.pattern('[\\w\\-\\s\\/]+')
      ]))
    });

    this.plants2 = []
  }

  ngOnInit(): void {

    this.getTopics();
    this.systemStart();
  }

  getTopics() {
    this.plants2 = []
    this.resourceService.getTopics().subscribe(
      (data) => {
        for (const x in data) {
          data[x]['id'] = x;
          if (x == 'plant1' || x == 'plant2' || x == 'plant3' || x == 'plant4' || x == 'plant5') {
            data[x]['imageUrl'] = '../../assets/images/' + x + '.jpeg';
          } else {
            data[x]['imageUrl'] = '../../assets/images/default.jpeg';
          }
          this.plants2.push(data[x])
        }
      },
      error => {
        console.log(error);
      }
    );
  }

  private systemStart() {
    this.resourceService.startSystem().subscribe(
      (data) => {
        // console.log(data);
      },
      error => {
        console.log(error);
      }
    );
  }

  public addPlant(plant: any) {

    this.resourceService.addPlant(JSON.stringify(plant)).subscribe(
      (data) => {
        document.getElementById("modalClose")?.click();
        this.getTopics();

        this.form = new FormGroup({
          id: new FormControl(uuidv4()),
          name: new FormControl('', Validators.compose([
            Validators.required,
            Validators.pattern('[\\w\\-\\s\\/]+')
          ]))
        });
      },
      error => {
        console.log(error);
      }
    );

  }
}
